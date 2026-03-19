"""Data Pipeline Service for NeuroQuant."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

import redis.asyncio as redis
import yfinance as yf
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.core.database import get_session
from app.models.ohlcv import OHLCV

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger(__name__)

MARKET_TZ = ZoneInfo(settings.MARKET_TIMEZONE)

app = FastAPI(title="NeuroQuant Data Pipeline", version="1.0.0")
scheduler = AsyncIOScheduler(timezone=MARKET_TZ)
redis_client: redis.Redis | None = None

pipeline_state: dict[str, Any] = {
    "last_fetch_started_at": None,
    "last_fetch_completed_at": None,
    "last_fetch_exchange": None,
    "last_records_inserted": 0,
    "last_published_updates": 0,
    "last_errors": [],
}


@dataclass(slots=True)
class FetchStats:
    """In-memory fetch statistics for a single pipeline run."""

    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    symbols_processed: int = 0
    records_inserted: int = 0
    published_updates: int = 0
    errors: list[str] = field(default_factory=list)


class DataFetchRequest(BaseModel):
    """Request model for manual data fetch."""

    symbols: list[str] = Field(min_length=1)
    start_date: str | None = None
    end_date: str | None = None
    interval: str = settings.DEFAULT_FETCH_INTERVAL
    exchange: str | None = None


class DataFetchResponse(BaseModel):
    """Response model for data fetch operations."""

    symbols_processed: int
    records_inserted: int
    published_updates: int
    errors: list[str]
    started_at: str
    completed_at: str


async def _get_redis_client() -> redis.Redis:
    """Get or initialize the shared Redis client."""

    global redis_client

    if redis_client is None:
        redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

    return redis_client


def _market_open_time() -> time:
    return time(settings.NSE_MARKET_OPEN_HOUR, settings.NSE_MARKET_OPEN_MINUTE)


def _market_close_time() -> time:
    return time(settings.NSE_MARKET_CLOSE_HOUR, settings.NSE_MARKET_CLOSE_MINUTE)


def _normalize_timestamp(value: Any) -> datetime:
    """Normalize timestamps to UTC for storage and downstream fanout."""

    if hasattr(value, "to_pydatetime"):
        dt_value = value.to_pydatetime()
    elif isinstance(value, datetime):
        dt_value = value
    else:
        dt_value = datetime.fromisoformat(str(value))

    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=MARKET_TZ)

    return dt_value.astimezone(UTC)


def _resolve_exchange(symbol: str, explicit_exchange: str | None = None) -> str:
    """Infer the exchange for a symbol when not supplied explicitly."""

    if explicit_exchange:
        return explicit_exchange.upper()
    if symbol.endswith(".NS"):
        return "NSE"
    if symbol.endswith("-USD"):
        return "CRYPTO"
    return "GLOBAL"


def is_market_hours(now: datetime | None = None) -> bool:
    """Check whether the NSE cash session is currently open."""

    current = now or datetime.now(MARKET_TZ)
    localized = current.astimezone(MARKET_TZ) if current.tzinfo else current.replace(tzinfo=MARKET_TZ)

    if localized.weekday() >= 5:
        return False

    return _market_open_time() <= localized.time() <= _market_close_time()


def _download_symbol_history(
    symbol: str,
    *,
    period: str,
    interval: str,
    start_date: str | None,
    end_date: str | None,
):
    """Download OHLCV data synchronously for use inside asyncio.to_thread."""

    if start_date or end_date:
        return yf.download(
            symbol,
            start=start_date,
            end=end_date,
            interval=interval,
            progress=False,
            auto_adjust=False,
            threads=False,
        )

    return yf.download(
        symbol,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=False,
        threads=False,
    )


def _build_records(symbol: str, exchange: str, data: Any) -> list[dict[str, Any]]:
    """Convert yfinance OHLCV data into database-ready records."""

    if getattr(data, "empty", True):
        return []

    records: list[dict[str, Any]] = []
    for timestamp, row in data.iterrows():
        open_price = row.get("Open")
        high_price = row.get("High")
        low_price = row.get("Low")
        close_price = row.get("Close")
        volume = row.get("Volume")

        if any(value is None for value in (open_price, high_price, low_price, close_price)):
            continue

        records.append(
            {
                "time": _normalize_timestamp(timestamp),
                "symbol": symbol,
                "exchange": exchange,
                "open": float(open_price),
                "high": float(high_price),
                "low": float(low_price),
                "close": float(close_price),
                "volume": int(volume or 0),
            }
        )

    return records


def _build_tick_payload(record: dict[str, Any], previous_close: float | None) -> dict[str, Any]:
    """Create the WebSocket/Redis tick payload for a latest OHLCV bar."""

    current_close = float(record["close"])
    reference_close = previous_close if previous_close and previous_close > 0 else float(record["open"])
    change_pct = ((current_close - reference_close) / reference_close) * 100 if reference_close else 0.0

    return {
        "type": "tick",
        "symbol": record["symbol"],
        "exchange": record["exchange"],
        "price": round(current_close, 4),
        "volume": int(record["volume"]),
        "change_pct": round(change_pct, 4),
        "timestamp": record["time"].isoformat(),
    }


async def publish_price_update(message: dict[str, Any]) -> None:
    """Publish a price update to symbol-specific and global Redis channels."""

    client = await _get_redis_client()
    encoded_message = json.dumps(message)

    await client.publish(f"ticks:{message['symbol']}", encoded_message)
    await client.publish("market:all", encoded_message)
    await client.publish("websocket_broadcast", encoded_message)


async def fetch_and_store_data(
    symbols: list[str],
    *,
    exchange: str | None = None,
    period: str | None = None,
    interval: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> FetchStats:
    """Fetch data from yfinance and upsert it into TimescaleDB."""

    stats = FetchStats()
    pipeline_state["last_fetch_started_at"] = stats.started_at.isoformat()
    pipeline_state["last_fetch_exchange"] = exchange or "MIXED"

    async with get_session() as session:
        for symbol in symbols:
            resolved_exchange = _resolve_exchange(symbol, exchange)

            try:
                data = await asyncio.to_thread(
                    _download_symbol_history,
                    symbol,
                    period=period or settings.DEFAULT_FETCH_PERIOD,
                    interval=interval or settings.DEFAULT_FETCH_INTERVAL,
                    start_date=start_date,
                    end_date=end_date,
                )
                records = _build_records(symbol, resolved_exchange, data)

                if not records:
                    stats.errors.append(f"No data returned for {symbol}")
                    continue

                stmt = insert(OHLCV).values(records).on_conflict_do_nothing(
                    index_elements=["time", "symbol", "exchange"]
                )
                result = await session.execute(stmt)
                await session.commit()

                inserted_count = int(result.rowcount or 0)
                stats.symbols_processed += 1
                stats.records_inserted += inserted_count

                latest_record = records[-1]
                previous_close = records[-2]["close"] if len(records) > 1 else None
                await publish_price_update(_build_tick_payload(latest_record, previous_close))
                stats.published_updates += 1

                logger.info(
                    "Fetched symbol data",
                    extra={
                        "symbol": symbol,
                        "exchange": resolved_exchange,
                        "records_downloaded": len(records),
                        "records_inserted": inserted_count,
                    },
                )
            except Exception as exc:
                await session.rollback()
                message = f"Error fetching {symbol}: {exc}"
                stats.errors.append(message)
                logger.exception(message)

    stats.completed_at = datetime.now(UTC)
    pipeline_state["last_fetch_completed_at"] = stats.completed_at.isoformat()
    pipeline_state["last_records_inserted"] = stats.records_inserted
    pipeline_state["last_published_updates"] = stats.published_updates
    pipeline_state["last_errors"] = stats.errors[-20:]

    return stats


async def fetch_market_data() -> FetchStats:
    """Fetch the configured NSE universe during active market hours."""

    if not is_market_hours():
        logger.info("Skipping NSE fetch outside market hours")
        return FetchStats(completed_at=datetime.now(UTC))

    return await fetch_and_store_data(settings.NSE_SYMBOLS, exchange="NSE")


async def fetch_crypto_data() -> FetchStats:
    """Fetch the configured crypto universe."""

    return await fetch_and_store_data(settings.CRYPTO_SYMBOLS, exchange="CRYPTO")


async def simulate_price_updates() -> int:
    """Republish last close values during off-hours to keep clients synchronized."""

    if is_market_hours():
        return 0

    published = 0
    async with get_session() as session:
        latest_time_subquery = (
            select(
                OHLCV.symbol.label("symbol"),
                OHLCV.exchange.label("exchange"),
                func.max(OHLCV.time).label("latest_time"),
            )
            .group_by(OHLCV.symbol, OHLCV.exchange)
            .subquery()
        )

        latest_records_query = (
            select(OHLCV)
            .join(
                latest_time_subquery,
                (OHLCV.symbol == latest_time_subquery.c.symbol)
                & (OHLCV.exchange == latest_time_subquery.c.exchange)
                & (OHLCV.time == latest_time_subquery.c.latest_time),
            )
            .order_by(OHLCV.symbol.asc())
        )
        latest_records = (await session.execute(latest_records_query)).scalars().all()

        for record in latest_records:
            previous_close_query = (
                select(OHLCV.close)
                .where(
                    OHLCV.symbol == record.symbol,
                    OHLCV.exchange == record.exchange,
                    OHLCV.time < record.time,
                )
                .order_by(OHLCV.time.desc())
                .limit(1)
            )
            previous_close_result = await session.execute(previous_close_query)
            previous_close = previous_close_result.scalar_one_or_none()

            await publish_price_update(
                _build_tick_payload(
                    {
                        "symbol": record.symbol,
                        "exchange": record.exchange,
                        "close": float(record.close),
                        "open": float(record.open),
                        "volume": int(record.volume),
                        "time": record.time,
                    },
                    float(previous_close) if previous_close is not None else None,
                )
            )
            published += 1

    pipeline_state["last_published_updates"] = published
    return published


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize scheduler and warm the Redis connection."""

    client = await _get_redis_client()
    await client.ping()

    if not scheduler.running:
        scheduler.add_job(
            fetch_market_data,
            CronTrigger(
                day_of_week="mon-fri",
                hour=f"{settings.NSE_MARKET_OPEN_HOUR}-{settings.NSE_MARKET_CLOSE_HOUR}",
                minute=f"*/{settings.FETCH_INTERVAL_MINUTES}",
                timezone=MARKET_TZ,
            ),
            id="nse_data_refresh",
            name="NSE Market Data Refresh",
            replace_existing=True,
            max_instances=1,
        )
        scheduler.add_job(
            fetch_crypto_data,
            CronTrigger(minute="*/30", timezone=UTC),
            id="crypto_data_refresh",
            name="Crypto Market Data Refresh",
            replace_existing=True,
            max_instances=1,
        )
        scheduler.add_job(
            simulate_price_updates,
            CronTrigger(minute=f"*/{settings.OFF_HOURS_PUBLISH_INTERVAL_MINUTES}", timezone=UTC),
            id="off_hours_republish",
            name="Off Hours Last Close Republishing",
            replace_existing=True,
            max_instances=1,
        )
        scheduler.start()

    logger.info("Data pipeline scheduler started")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Shutdown scheduler and Redis client."""

    global redis_client

    if scheduler.running:
        scheduler.shutdown(wait=False)

    if redis_client is not None:
        await redis_client.close()
        redis_client = None

    logger.info("Data pipeline scheduler stopped")


@app.post(
    "/api/v1/data/fetch",
    response_model=DataFetchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def manual_data_fetch(request: DataFetchRequest) -> DataFetchResponse:
    """Manually trigger data fetch for specific symbols."""

    stats = await fetch_and_store_data(
        request.symbols,
        exchange=request.exchange,
        interval=request.interval,
        start_date=request.start_date,
        end_date=request.end_date,
    )

    return DataFetchResponse(
        symbols_processed=stats.symbols_processed,
        records_inserted=stats.records_inserted,
        published_updates=stats.published_updates,
        errors=stats.errors,
        started_at=stats.started_at.isoformat(),
        completed_at=(stats.completed_at or datetime.now(UTC)).isoformat(),
    )


@app.get("/api/v1/data/status")
async def get_data_status() -> dict[str, Any]:
    """Get runtime state for the data pipeline scheduler and last fetch."""

    jobs = [
        {
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        }
        for job in scheduler.get_jobs()
    ]

    return {
        "scheduler_running": scheduler.running,
        "market_open": is_market_hours(),
        "jobs": jobs,
        **pipeline_state,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)