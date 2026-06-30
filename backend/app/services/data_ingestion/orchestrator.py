"""Concurrent data-ingestion orchestrator with retry and persistence."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.data_ingestion.alpha_vantage_source import AlphaVantageSource
from app.services.data_ingestion.base import DataSourceError, Interval, MarketDataSource, OHLCVBar
from app.services.data_ingestion.coingecko_source import CoinGeckoSource
from app.services.data_ingestion.fred_source import FREDSource
from app.services.data_ingestion.nse_source import NSESource
from app.services.data_ingestion.yfinance_source import YFinanceSource
from app.services.data_ingestion.stooq_source import StooqSource

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class IngestionTask:
    symbol: str
    interval: Interval
    start: datetime
    end: datetime
    asset_type: str


class DataIngestionOrchestrator:
    """Coordinate concurrent fetches with source routing and retries."""

    def __init__(self, max_concurrency: int = 8) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._sources: dict[str, MarketDataSource] = {
            "yfinance": YFinanceSource(),
            "coingecko": CoinGeckoSource(),
            "fred": FREDSource(),
            "alpha_vantage": AlphaVantageSource(),
            "nse": NSESource(),
            "stooq": StooqSource(),
        }

    def _select_sources(self, task: IngestionTask) -> list[MarketDataSource]:
        if task.asset_type == "CRYPTO":
            return [self._sources["coingecko"], self._sources["yfinance"]]
        if task.asset_type == "MACRO":
            return [self._sources["fred"]]
        if task.symbol.endswith(".NS") or task.symbol in {"^NSEI", "^BSESN"}:
            return [self._sources["nse"], self._sources["yfinance"], self._sources["stooq"]]
        return [self._sources["yfinance"], self._sources["stooq"]]

    async def _fetch_with_retry(self, source: MarketDataSource, task: IngestionTask, max_attempts: int = 3) -> list[OHLCVBar]:
        last_error: Exception | None = None
        for attempt in range(1, max_attempts + 1):
            try:
                async with self._semaphore:
                    return await source.fetch_ohlcv(task.symbol, task.interval, task.start, task.end)
            except Exception as exc:
                last_error = exc
                await asyncio.sleep(min(2**attempt, 8))

        raise DataSourceError(f"{source.name} failed for {task.symbol}: {last_error}")

    async def fetch_task(self, task: IngestionTask) -> tuple[str, list[OHLCVBar]]:
        # Check cache first
        cache_key = f"ingest:bars:{task.symbol.upper()}:{task.interval}:{task.start.strftime('%Y%m%d')}:{task.end.strftime('%Y%m%d')}"
        redis = None
        try:
            from app.database.redis_client import get_redis_client
            redis = await get_redis_client()
            cached = await redis.get(cache_key)
            if cached:
                cached_data = json.loads(cached)
                source_name = cached_data["source"]
                bars = [
                    OHLCVBar(
                        time=datetime.fromisoformat(b["time"]),
                        open=b["open"],
                        high=b["high"],
                        low=b["low"],
                        close=b["close"],
                        volume=b["volume"],
                        adjusted_close=b["adjusted_close"],
                        interval=b["interval"]
                    )
                    for b in cached_data["bars"]
                ]
                return source_name, bars
        except Exception as e:
            logger.warning(f"Redis cache check failed in Ingestion Orchestrator: {e}")

        errors: list[str] = []
        for source in self._select_sources(task):
            try:
                bars = await self._fetch_with_retry(source, task)
                if bars:
                    # Store in cache
                    if redis:
                        try:
                            serialized = {
                                "source": source.name,
                                "bars": [
                                    {
                                        "time": b.time.isoformat(),
                                        "open": b.open,
                                        "high": b.high,
                                        "low": b.low,
                                        "close": b.close,
                                        "volume": b.volume,
                                        "adjusted_close": b.adjusted_close,
                                        "interval": b.interval
                                    }
                                    for b in bars
                                ]
                            }
                            await redis.setex(cache_key, 3600, json.dumps(serialized))
                        except Exception as e:
                            logger.warning(f"Failed to write to Redis in Ingestion Orchestrator: {e}")
                    return source.name, bars
                errors.append(f"{source.name}: empty")
            except Exception as exc:
                errors.append(f"{source.name}: {exc}")

        raise DataSourceError(f"No source returned data for {task.symbol}. Details: {' | '.join(errors)}")

    async def fetch_many(self, tasks: list[IngestionTask]) -> dict[str, dict[str, Any]]:
        coroutines = [self.fetch_task(task) for task in tasks]
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        output: dict[str, dict[str, Any]] = {}
        for task, result in zip(tasks, results, strict=True):
            if isinstance(result, Exception):
                output[task.symbol] = {"ok": False, "error": str(result), "bars": []}
            else:
                source_name, bars = result
                output[task.symbol] = {"ok": True, "source": source_name, "bars": bars}
        return output

    async def persist_ohlcv(self, session: AsyncSession, symbol_id: int, bars: list[OHLCVBar]) -> int:
        if not bars:
            return 0

        stmt = text(
            """
            INSERT INTO ohlcv (time, symbol_id, open, high, low, close, volume, adjusted_close, interval)
            VALUES (:time, :symbol_id, :open, :high, :low, :close, :volume, :adjusted_close, :interval)
            ON CONFLICT (time, symbol_id, interval)
            DO UPDATE SET
              open = EXCLUDED.open,
              high = EXCLUDED.high,
              low = EXCLUDED.low,
              close = EXCLUDED.close,
              volume = EXCLUDED.volume,
              adjusted_close = EXCLUDED.adjusted_close
            """
        )

        payload = [
            {
                "time": bar.time,
                "symbol_id": symbol_id,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
                "adjusted_close": bar.adjusted_close,
                "interval": bar.interval,
            }
            for bar in bars
        ]

        await session.execute(stmt, payload)
        return len(payload)
