"""Celery tasks for background market data ingestion."""

import asyncio
import logging
import random
from datetime import UTC, datetime, timedelta

from celery import shared_task
from sqlalchemy import select

from app.database.connection import get_db
from app.models.instrument import Instrument
from app.models.market import Exchange
from app.models.ohlcv import OHLCV
from app.services.ingestion.provider_manager import provider_manager

logger = logging.getLogger(__name__)

_EXCHANGE_DEFAULTS = {
    "NSE": {"name": "National Stock Exchange", "country": "IN", "timezone": "Asia/Kolkata"},
    "BSE": {"name": "Bombay Stock Exchange", "country": "IN", "timezone": "Asia/Kolkata"},
}


async def _get_or_create_exchange(session, code: str) -> Exchange:
    stmt = select(Exchange).where(Exchange.code == code)
    result = await session.execute(stmt)
    exchange = result.scalar_one_or_none()
    if exchange:
        return exchange

    defaults = _EXCHANGE_DEFAULTS.get(code, {"name": code, "country": "IN", "timezone": "UTC"})
    exchange = Exchange(code=code, **defaults)
    session.add(exchange)
    await session.flush()
    return exchange


async def _seed_universe_async():
    nse_provider = next((p for p in provider_manager.providers if p.name == "nse"), None)
    if not nse_provider:
        logger.error("NSE provider not found")
        return

    universe = await nse_provider.get_universe()
    if not universe:
        logger.warning("No universe data fetched")
        return

    async for session in get_db():
        count = 0
        exchange_cache: dict[str, Exchange] = {}
        for item in universe:
            stmt = select(Instrument).where(Instrument.canonical_symbol == item["symbol"])
            result = await session.execute(stmt)
            instrument = result.scalar_one_or_none()
            if not instrument:
                exchange_code = item["exchange"]
                exchange = exchange_cache.get(exchange_code)
                if not exchange:
                    exchange = await _get_or_create_exchange(session, exchange_code)
                    exchange_cache[exchange_code] = exchange

                instrument = Instrument(
                    canonical_symbol=item["symbol"],
                    display_name=item["display_name"],
                    exchange_id=exchange.id,
                    is_active=True,
                )
                session.add(instrument)
                count += 1
        await session.commit()
        logger.info(f"Seeded {count} new instruments")


@shared_task(name="market_data.seed_universe")
def seed_universe():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(_seed_universe_async())
    return {"status": "success"}


async def _backfill_historical_data_async():
    async for session in get_db():
        stmt = select(Instrument).where(Instrument.is_active)
        result = await session.execute(stmt)
        instruments = result.scalars().all()

        start = datetime.now(UTC) - timedelta(days=5 * 365)
        end = datetime.now(UTC)

        for inst in instruments:
            logger.info(f"Backfilling {inst.canonical_symbol}...")
            try:
                bars = await provider_manager.get_ohlcv(inst.canonical_symbol, "1d", start, end)
                if bars:
                    # In a real app we'd bulk upsert
                    for bar in bars:
                        # Check if exists
                        exist_stmt = select(OHLCV).where(
                            OHLCV.instrument_id == inst.id,
                            OHLCV.timestamp == bar.time,
                            OHLCV.interval == "1d",
                        )
                        exist_res = await session.execute(exist_stmt)
                        if not exist_res.scalar_one_or_none():
                            ohlcv = OHLCV(
                                instrument_id=inst.id,
                                timestamp=bar.time,
                                interval="1d",
                                open=bar.open,
                                high=bar.high,
                                low=bar.low,
                                close=bar.close,
                                volume=bar.volume,
                                provider="multi_provider",
                            )
                            session.add(ohlcv)
                    await session.commit()
                # Jitter to avoid hammering provider
                await asyncio.sleep(random.uniform(0.5, 2.0))
            except Exception as e:
                logger.error(f"Failed backfilling {inst.canonical_symbol}: {e}")
                await session.rollback()


@shared_task(name="market_data.backfill_historical_data")
def backfill_historical_data():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(_backfill_historical_data_async())
    return {"status": "success"}
