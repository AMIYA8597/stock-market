import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from app.database.connection import async_session_factory
from app.models.instrument import Instrument
from app.models.ohlcv import OHLCV


async def ingest():
    async with async_session_factory() as session:
        result = await session.execute(select(Instrument).limit(5))
        instruments = {i.symbol: i.id for i in result.scalars().all()}

        # We will just generate random walk data for these 5 symbols since they might not be on yahoo finance.
        dates = pd.date_range(start="2020-01-01", periods=200, freq="B")
        for _symbol, s_id in instruments.items():
            np.random.seed(42 + s_id)
            returns = np.random.normal(loc=0.0001, scale=0.02, size=200)
            price = 100 * np.exp(np.cumsum(returns))

            df = pd.DataFrame({
                "time": dates,
                "open": price * np.random.uniform(0.99, 1.01, size=200),
                "high": price * np.random.uniform(1.0, 1.03, size=200),
                "low": price * np.random.uniform(0.97, 1.0, size=200),
                "close": price,
                "volume": np.random.randint(1000, 1000000, size=200).astype(float),
            })

            records = []
            for _, row in df.iterrows():
                records.append({
                    "time": row["time"],
                    "symbol_id": s_id,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                    "interval": "1d"
                })

            if records:
                stmt = insert(OHLCV).values(records).on_conflict_do_nothing(
                    index_elements=["time", "symbol_id", "interval"]
                )
                await session.execute(stmt)

        await session.commit()
        print("Ingestion complete")

if __name__ == "__main__":
    asyncio.run(ingest())
