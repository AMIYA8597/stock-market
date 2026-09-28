"""Sync Upstox's published NSE equity instrument master into InstrumentAlias rows.

Upstox publishes a free, unauthenticated instrument master file per exchange
(no Analytics Token needed for this specific file) at
https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz -
a gzipped JSON array of every tradable NSE instrument, each carrying the
instrument_key (e.g. "NSE_EQ|INE002A01018") that UpstoxSource needs to
resolve a canonical_symbol into an actual API call (see
app/services/ingestion/upstox_source.py's _resolve_instrument_key).

NOTE ON FIELD NAMES: like upstox_source.py, the exact field names below
follow Upstox's documented instrument file schema but have not been
verified against a live download - this environment's egress proxy blocks
assets.upstox.com the same way it blocks api.upstox.com. The first real run
(from Cloud Run, which has real internet access) should be checked against
actual field names and this comment removed once confirmed.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import logging

import httpx
from celery import shared_task
from sqlalchemy import select

from app.database.connection import get_db
from app.models.market import Exchange, Instrument, InstrumentAlias

logger = logging.getLogger(__name__)

_INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"


async def _fetch_upstox_nse_instruments() -> list[dict]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(_INSTRUMENTS_URL)
        resp.raise_for_status()
        raw = gzip.decompress(resp.content)
        return json.loads(raw)


def _is_nse_equity(item: dict) -> bool:
    exchange = (item.get("exchange") or item.get("segment") or "").upper()
    instrument_type = (item.get("instrument_type") or "").upper()
    return exchange in ("NSE_EQ", "NSE") and instrument_type in ("EQ", "")


async def _sync_upstox_instruments_async(create_missing: bool = True) -> dict:
    instruments = await _fetch_upstox_nse_instruments()
    equities = [item for item in instruments if _is_nse_equity(item)]

    matched = 0
    skipped_no_instrument = 0
    already_aliased = 0
    created_instruments = 0

    async for session in get_db():
        result = await session.execute(select(Exchange).where(Exchange.code == "NSE"))
        exchange = result.scalar_one_or_none()
        if not exchange:
            exchange = Exchange(
                code="NSE", name="National Stock Exchange", country="IN", timezone="Asia/Kolkata"
            )
            session.add(exchange)
            await session.flush()

        for item in equities:
            trading_symbol = item.get("trading_symbol") or item.get("tradingsymbol")
            instrument_key = item.get("instrument_key")
            if not trading_symbol or not instrument_key:
                continue

            inst_result = await session.execute(
                select(Instrument).where(Instrument.canonical_symbol == trading_symbol)
            )
            instrument = inst_result.scalar_one_or_none()

            if not instrument:
                if not create_missing:
                    skipped_no_instrument += 1
                    continue
                instrument = Instrument(
                    canonical_symbol=trading_symbol,
                    display_name=item.get("name") or trading_symbol,
                    exchange_id=exchange.id,
                    market_segment="EQ",
                    asset_class="equity",
                    isin=item.get("isin"),
                    is_active=True,
                )
                session.add(instrument)
                await session.flush()
                created_instruments += 1

            alias_result = await session.execute(
                select(InstrumentAlias).where(
                    InstrumentAlias.provider == "upstox",
                    InstrumentAlias.provider_symbol == instrument_key,
                )
            )
            if alias_result.scalar_one_or_none():
                already_aliased += 1
                continue

            session.add(
                InstrumentAlias(
                    instrument_id=instrument.id,
                    provider="upstox",
                    alias_type="instrument_key",
                    provider_symbol=instrument_key,
                    is_primary=True,
                )
            )
            matched += 1

        await session.commit()

    result = {
        "total_upstox_equities": len(equities),
        "new_aliases_created": matched,
        "already_aliased": already_aliased,
        "new_instruments_created": created_instruments,
        "skipped_no_instrument": skipped_no_instrument,
    }
    logger.info(f"upstox_instrument_sync_complete {result}")
    return result


@shared_task(name="market_data.sync_upstox_instruments")
def sync_upstox_instruments(create_missing: bool = True):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(_sync_upstox_instruments_async(create_missing=create_missing))
