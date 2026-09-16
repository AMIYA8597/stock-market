"""Provider manager orchestrating failover and caching for market data."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.database.redis_client import cache_get, cache_set, get_redis_client
from app.services.data_ingestion.base import (
    DataUnavailableError,
    Interval,
    OHLCVBar,
    ProviderError,
    Quote,
)
from app.services.data_ingestion.nse_source import NSESource
from app.services.data_ingestion.stooq_source import StooqProvider
from app.services.data_ingestion.yfinance_source import YFinanceProvider

logger = logging.getLogger(__name__)


class ProviderManager:
    """Orchestrates market data providers with failover and cache-aside logic."""

    def __init__(self):
        # Order: yfinance -> nse -> stooq
        self.providers = [YFinanceProvider(), NSESource(), StooqProvider()]
        # TTL definitions (seconds)
        self.ttls = {"quote": 10, "intraday": 60, "daily": 24 * 60 * 60, "index": 30}

    async def get_quote(self, symbol: str) -> Quote:
        """Fetch quote with cache and failover."""
        redis = await get_redis_client()
        cache_key = f"market:quote:{symbol}"

        # Check cache
        cached = await cache_get(redis, cache_key)
        if cached:
            # We enforce stale-while-revalidate pattern
            as_of = (
                datetime.fromisoformat(cached["as_of"])
                if isinstance(cached["as_of"], str)
                else cached["as_of"]
            )
            if (datetime.now(UTC) - as_of).total_seconds() > self.ttls["quote"]:
                # Stale: kick off background refresh, return stale for now
                asyncio.create_task(self._fetch_and_cache_quote(symbol, cache_key))
            return Quote(
                symbol=cached["symbol"],
                price=cached["price"],
                change=cached["change"],
                change_pct=cached["change_pct"],
                volume=cached["volume"],
                timestamp=as_of,
            )

        # Cache miss, fetch synchronous
        return await self._fetch_and_cache_quote(symbol, cache_key)

    async def _fetch_and_cache_quote(self, symbol: str, cache_key: str) -> Quote:
        redis = await get_redis_client()
        for provider in self.providers:
            try:
                quote = await provider.get_quote(symbol)
                # Cache it
                await cache_set(
                    redis,
                    cache_key,
                    {
                        "symbol": quote.symbol,
                        "price": quote.price,
                        "change": quote.change,
                        "change_pct": quote.change_pct,
                        "volume": quote.volume,
                        "as_of": quote.timestamp.isoformat(),
                        "source": provider.name,
                    },
                    ttl=timedelta(days=1),
                )  # Keep physically cached for 1 day, stale after 10s
                return quote
            except ProviderError as e:
                logger.warning(f"{provider.name} failed quote for {symbol}: {e}")
            except Exception as e:
                logger.error(f"{provider.name} unexpected error on quote {symbol}: {e}")

        raise DataUnavailableError(f"All providers failed to fetch quote for {symbol}")

    async def get_ohlcv(
        self, symbol: str, interval: Interval, start: datetime, end: datetime
    ) -> list[OHLCVBar]:
        """Fetch OHLCV with cache and failover."""
        redis = await get_redis_client()
        cache_key = f"market:ohlcv:{symbol}:{interval}:{start.date()}:{end.date()}"

        cached = await cache_get(redis, cache_key)
        ttl_seconds = self.ttls["daily"] if interval == "1d" else self.ttls["intraday"]

        if cached:
            as_of = datetime.fromisoformat(cached["as_of"])
            if (datetime.now(UTC) - as_of).total_seconds() > ttl_seconds:
                asyncio.create_task(
                    self._fetch_and_cache_ohlcv(symbol, interval, start, end, cache_key)
                )

            bars = []
            for b in cached["bars"]:
                bars.append(
                    OHLCVBar(
                        time=datetime.fromisoformat(b["time"]),
                        open=b["open"],
                        high=b["high"],
                        low=b["low"],
                        close=b["close"],
                        volume=b["volume"],
                        adjusted_close=b.get("adjusted_close"),
                        interval=interval,
                    )
                )
            return bars

        return await self._fetch_and_cache_ohlcv(symbol, interval, start, end, cache_key)

    async def _fetch_and_cache_ohlcv(
        self, symbol: str, interval: Interval, start: datetime, end: datetime, cache_key: str
    ) -> list[OHLCVBar]:
        redis = await get_redis_client()
        for provider in self.providers:
            try:
                bars = await provider.get_ohlcv(symbol, interval, start, end)
                if not bars:
                    continue
                # Cache it
                cached_bars = []
                for b in bars:
                    cached_bars.append(
                        {
                            "time": b.time.isoformat(),
                            "open": b.open,
                            "high": b.high,
                            "low": b.low,
                            "close": b.close,
                            "volume": b.volume,
                            "adjusted_close": b.adjusted_close,
                        }
                    )

                await cache_set(
                    redis,
                    cache_key,
                    {
                        "bars": cached_bars,
                        "as_of": datetime.now(UTC).isoformat(),
                        "source": provider.name,
                    },
                    ttl=timedelta(days=7),
                )  # physical ttl
                return bars
            except ProviderError as e:
                logger.warning(f"{provider.name} failed ohlcv for {symbol}: {e}")
            except Exception as e:
                logger.error(f"{provider.name} unexpected error on ohlcv {symbol}: {e}")

        raise DataUnavailableError(f"All providers failed to fetch OHLCV for {symbol}")

    async def get_providers_health(self) -> dict[str, Any]:
        """Health check for all providers."""
        tasks = [p.health() for p in self.providers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        health_data = {}
        for p, res in zip(self.providers, results, strict=False):
            if isinstance(res, Exception):
                health_data[p.name] = {"status": "down", "error": str(res)}
            else:
                health_data[p.name] = res
        return health_data


provider_manager = ProviderManager()
