"""Instrument seeder — populates Instrument + InstrumentAlias tables.

Downloads the Upstox NSE/BSE instrument master CSV (publicly accessible,
no auth required) and upserts every EQ/INDEX row into the canonical DB.
Run once on startup if the tables are empty; subsequent runs are idempotent
(ON CONFLICT DO NOTHING for both instruments and aliases).

CSV source: https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz
Columns: instrument_key, exchange_token, tradingsymbol, name, last_price,
         expiry, strike, tick_size, lot_size, instrument_type, option_type, exchange
"""

from __future__ import annotations

import asyncio
import gzip
import io
import logging
import uuid
from datetime import UTC, datetime

import aiohttp

logger = logging.getLogger(__name__)

# Upstox public instrument master CSVs — no auth required
_UPSTOX_INSTRUMENT_CSV_URLS = {
    "NSE": "https://assets.upstox.com/market-quote/instruments/exchange/NSE.csv.gz",
    "BSE": "https://assets.upstox.com/market-quote/instruments/exchange/BSE.csv.gz",
}

# Exchange metadata
_EXCHANGE_META = {
    "NSE": {"name": "National Stock Exchange of India", "country": "IN", "timezone": "Asia/Kolkata"},
    "BSE": {"name": "Bombay Stock Exchange", "country": "IN", "timezone": "Asia/Kolkata"},
}

# Only seed these instrument types (skip futures, options, etc.)
_WANTED_TYPES = {"EQ", "INDEX", "SM", "MF"}

_seed_lock = asyncio.Lock()
_seeded: set[str] = set()  # tracks which exchanges have been seeded this session


async def _download_csv(url: str) -> list[dict]:
    """Download and parse a gzipped CSV from Upstox."""
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Failed to download {url}: HTTP {resp.status}")
            raw = await resp.read()

    # Decompress gzip
    with gzip.open(io.BytesIO(raw), "rt", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    if not lines:
        return []

    header = [h.strip().strip('"') for h in lines[0].split(",")]
    rows = []
    for line in lines[1:]:
        parts = line.strip().split(",")
        if len(parts) < len(header):
            continue
        row = {}
        for i, key in enumerate(header):
            row[key] = parts[i].strip().strip('"') if i < len(parts) else ""
        rows.append(row)
    return rows


async def seed_instruments_from_upstox(exchange_code: str = "NSE", force: bool = False) -> dict:
    """Download Upstox instrument master and seed Instrument + InstrumentAlias tables.

    Returns a summary dict: {"inserted_instruments": N, "inserted_aliases": N, "skipped": N}.
    Idempotent — safe to call repeatedly.
    """
    async with _seed_lock:
        if exchange_code in _seeded and not force:
            return {"status": "already_seeded", "exchange": exchange_code}

        url = _UPSTOX_INSTRUMENT_CSV_URLS.get(exchange_code)
        if not url:
            raise ValueError(f"Unknown exchange: {exchange_code}")

        logger.info(f"Downloading Upstox instrument master for {exchange_code}…")
        try:
            rows = await _download_csv(url)
        except Exception as e:
            logger.warning(f"Failed to download instrument master for {exchange_code}: {e}")
            return {"status": "download_failed", "error": str(e)}

        logger.info(f"Downloaded {len(rows)} rows for {exchange_code}, seeding DB…")

        from sqlalchemy import select

        from app.database.connection import async_session_factory
        from app.models.market import Exchange, Instrument, InstrumentAlias

        inserted_instruments = 0
        inserted_aliases = 0
        skipped = 0

        async with async_session_factory() as db:
            # Ensure Exchange row exists
            exch_res = await db.execute(select(Exchange).where(Exchange.code == exchange_code))
            exchange = exch_res.scalars().first()
            if not exchange:
                meta = _EXCHANGE_META.get(exchange_code, {"name": exchange_code, "country": "IN", "timezone": "Asia/Kolkata"})
                exchange = Exchange(
                    id=uuid.uuid4(),
                    code=exchange_code,
                    name=meta["name"],
                    country=meta["country"],
                    timezone=meta["timezone"],
                    is_active=True,
                )
                db.add(exchange)
                await db.flush()
                logger.info(f"Created Exchange row: {exchange_code}")

            exchange_id = exchange.id

            for row in rows:
                instrument_type = row.get("instrument_type", "").upper()
                if instrument_type not in _WANTED_TYPES:
                    skipped += 1
                    continue

                trading_symbol = row.get("tradingsymbol", "").strip()
                instrument_key = row.get("instrument_key", "").strip()
                name = row.get("name", "").strip() or trading_symbol

                if not trading_symbol or not instrument_key:
                    skipped += 1
                    continue

                # Canonical symbol (bare, no exchange suffix)
                canonical = trading_symbol.upper()

                # Asset class
                asset_class = "INDEX" if instrument_type == "INDEX" else "EQUITY"

                # Upsert Instrument
                inst_res = await db.execute(
                    select(Instrument).where(
                        Instrument.exchange_id == exchange_id,
                        Instrument.canonical_symbol == canonical,
                    )
                )
                instrument = inst_res.scalars().first()
                if not instrument:
                    instrument = Instrument(
                        id=uuid.uuid4(),
                        canonical_symbol=canonical,
                        display_name=name,
                        exchange_id=exchange_id,
                        market_segment=instrument_type,
                        asset_class=asset_class,
                        currency="INR",
                        isin=None,
                        is_active=True,
                        is_tradable=instrument_type == "EQ",
                        source_metadata={"upstox_key": instrument_key},
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC),
                    )
                    db.add(instrument)
                    await db.flush()
                    inserted_instruments += 1

                # Upsert InstrumentAlias
                alias_res = await db.execute(
                    select(InstrumentAlias).where(
                        InstrumentAlias.provider == "upstox",
                        InstrumentAlias.provider_symbol == instrument_key,
                    )
                )
                if not alias_res.scalars().first():
                    alias = InstrumentAlias(
                        id=uuid.uuid4(),
                        instrument_id=instrument.id,
                        provider="upstox",
                        alias_type="instrument_key",
                        provider_symbol=instrument_key,
                        is_primary=True,
                        created_at=datetime.now(UTC),
                    )
                    db.add(alias)
                    inserted_aliases += 1

            await db.commit()

        _seeded.add(exchange_code)
        logger.info(
            f"Instrument seeding complete for {exchange_code}: "
            f"{inserted_instruments} instruments, {inserted_aliases} aliases, {skipped} skipped"
        )
        return {
            "status": "ok",
            "exchange": exchange_code,
            "inserted_instruments": inserted_instruments,
            "inserted_aliases": inserted_aliases,
            "skipped": skipped,
        }


async def seed_all_exchanges(force: bool = False) -> dict:
    """Seed NSE + BSE instrument masters concurrently."""
    nse, bse = await asyncio.gather(
        seed_instruments_from_upstox("NSE", force=force),
        seed_instruments_from_upstox("BSE", force=force),
        return_exceptions=True,
    )
    return {"NSE": nse if not isinstance(nse, Exception) else str(nse),
            "BSE": bse if not isinstance(bse, Exception) else str(bse)}


async def ensure_seeded() -> None:
    """Run once at startup: seed if the instruments table is nearly empty."""
    try:
        from sqlalchemy import func, select

        from app.database.connection import async_session_factory
        from app.models.market import Instrument

        async with async_session_factory() as db:
            count = (await db.execute(select(func.count()).select_from(Instrument))).scalar_one()

        if count < 100:
            logger.info(f"Instruments table has only {count} rows — triggering full seed…")
            await seed_all_exchanges()
        else:
            logger.info(f"Instruments table has {count} rows — skipping seed.")
    except Exception as e:
        logger.warning(f"ensure_seeded failed (non-fatal): {e}")
