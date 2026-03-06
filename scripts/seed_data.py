#!/usr/bin/env python3
"""
NEUROQUANT Data Seeding Script
Seeds historical market data for NSE500, S&P500, and crypto
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

import yfinance as yf
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings
from backend.app.models.ohlcv import OHLCV

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Asset universes
NSE500 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "HINDUNILVR.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS", "AXISBANK.NS",
    # Add more NSE500 symbols...
]

SP500 = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "JPM", "JNJ", "V",
    # Add more S&P500...
]

CRYPTO = [
    "BTC-USD", "ETH-USD", "BNB-USD", "ADA-USD", "SOL-USD",
]

async def fetch_yahoo_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch OHLCV data from Yahoo Finance"""
    try:
        data = yf.download(symbol, start=start_date, end=end_date, progress=False)
        data = data.reset_index()
        data['symbol'] = symbol
        data['exchange'] = 'NSE' if '.NS' in symbol else ('CRYPTO' if '-USD' in symbol else 'NYSE')
        return data[['Date', 'symbol', 'exchange', 'Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception as e:
        logger.error(f"Failed to fetch {symbol}: {e}")
        return pd.DataFrame()

async def seed_ohlcv_data():
    """Seed OHLCV data for all assets"""
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=Session, expire_on_commit=False)

    start_date = (datetime.now() - timedelta(days=365*10)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')

    all_symbols = NSE500 + SP500 + CRYPTO

    async with async_session() as session:
        for symbol in all_symbols:
            logger.info(f"Seeding {symbol}...")
            df = await fetch_yahoo_data(symbol, start_date, end_date)

            if df.empty:
                continue

            # Convert to OHLCV records
            records = []
            for _, row in df.iterrows():
                record = OHLCV(
                    time=row['Date'].to_pydatetime(),
                    symbol=row['symbol'],
                    exchange=row['exchange'],
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=int(row['Volume'])
                )
                records.append(record)

            # Bulk insert
            session.add_all(records)
            await session.commit()

            logger.info(f"Seeded {len(records)} records for {symbol}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_ohlcv_data())