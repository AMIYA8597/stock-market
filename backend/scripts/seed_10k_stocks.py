import asyncio
import csv
import io
import os
import sys
import urllib.request

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database.connection import engine
from app.models.instrument import Instrument

# Official Zerodha Daily Instruments Dump
KITE_INSTRUMENTS_URL = "https://api.kite.trade/instruments"

async def seed_stocks():
    print("Fetching 10,000+ global symbols via HTTPS...")

    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        res = await db.execute(select(Instrument.symbol))
        existing_symbols = set(res.scalars().all())

        batch = []
        count = 0

        # Indian Stocks from Zerodha Dump
        try:
            req = urllib.request.Request(KITE_INSTRUMENTS_URL, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req)
            csv_data = response.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(csv_data))

            for row in reader:
                if row.get('exchange') != 'NSE':
                    continue
                if row.get('instrument_type') != 'EQ':
                    continue

                raw_symbol = row.get('tradingsymbol', '').strip().upper()
                if not raw_symbol:
                    continue

                clean_symbol = raw_symbol
                yfinance_ticker = f"{raw_symbol}.NS"

                if clean_symbol not in existing_symbols:
                    instrument = Instrument(
                        symbol=clean_symbol,
                        display_name=row.get('name', '')[:250] or f"{clean_symbol} Equity",
                        exchange="NSE",
                        yfinance_ticker=yfinance_ticker,
                        is_active=True
                    )
                    batch.append(instrument)
                    existing_symbols.add(clean_symbol)
                    count += 1

                if len(batch) >= 1000:
                    db.add_all(batch)
                    await db.commit()
                    print(f"Inserted {count} NSE stocks...")
                    batch = []
        except Exception as e:
            print(f"Error fetching NSE data: {e}")

        # Save all
        if batch:
            db.add_all(batch)
            await db.commit()
            print(f"Inserted {count} NSE stocks...")

        print(f"\nSuccessfully seeded {count} new stocks with live data connections ready!")

        # Verify total
        res = await db.execute(select(Instrument.symbol))
        total = len(res.scalars().all())
        print(f"Total live stocks now in database: {total}")

if __name__ == "__main__":
    asyncio.run(seed_stocks())
