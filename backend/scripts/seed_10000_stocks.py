import asyncio
import csv
import io
import sys
import urllib.request
from pathlib import Path

from loguru import logger

# Add backend root to sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from sqlalchemy import select

from app.database.connection import async_session_factory
from app.models.instrument import Instrument


async def seed_stocks():
    logger.info("Fetching NSE equity list...")
    nse_url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }

    symbols = []
    try:
        req = urllib.request.Request(nse_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            csv_data = response.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(csv_data))
            for row in reader:
                sym = row.get('SYMBOL', '').strip()
                name = row.get('NAME OF COMPANY', '').strip()
                if sym:
                    symbols.append({
                        "symbol": f"{sym}.NS",
                        "name": name,
                        "asset_class": "equity",
                        "exchange": "NSE"
                    })
    except Exception as e:
        logger.error(f"Failed to fetch real NSE list: {e}")
        symbols = [{"symbol": f"TEST{i}.NS", "name": f"Test Company {i}", "asset_class": "equity", "exchange": "NSE"} for i in range(1, 101)]

    current_count = len(symbols)
    target_count = 10000

    if current_count < target_count:
        logger.info(f"Generating {target_count - current_count} synthetic tickers...")
        for i in range(current_count + 1, target_count + 1):
            if i % 2 == 0:
                symbols.append({
                    "symbol": f"US{i}",
                    "name": f"US Global Corp {i}",
                    "asset_class": "equity",
                    "exchange": "NASDAQ"
                })
            else:
                symbols.append({
                    "symbol": f"BSE{i}.BO",
                    "name": f"BSE India Ltd {i}",
                    "asset_class": "equity",
                    "exchange": "BSE"
                })

    logger.info(f"Total symbols prepared: {len(symbols)}")

    async with async_session_factory() as session:
        count_res = await session.execute(select(Instrument))
        existing = count_res.scalars().all()
        existing_symbols = {e.symbol for e in existing}

        seen_symbols = set(existing_symbols)
        new_instruments = []
        for s in symbols:
            sym_clean = s["symbol"].split(".")[0]
            if sym_clean not in seen_symbols:
                seen_symbols.add(sym_clean)
                new_instruments.append(
                    Instrument(
                        symbol=sym_clean,
                        display_name=s["name"],
                        exchange=s["exchange"],
                        yfinance_ticker=s["symbol"],
                        is_active=True
                    )
                )

        if new_instruments:
            logger.info(f"Inserting {len(new_instruments)} new instruments into the database...")
            chunk_size = 1000
            for i in range(0, len(new_instruments), chunk_size):
                session.add_all(new_instruments[i:i+chunk_size])
                await session.commit()
                logger.info(f"Inserted chunk {i//chunk_size + 1}")
        else:
            logger.info("Database already contains the instruments.")

    logger.info("Seeding complete.")

if __name__ == "__main__":
    asyncio.run(seed_stocks())
