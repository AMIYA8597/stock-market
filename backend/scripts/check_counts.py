import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import func, select

from app.database.connection import async_session_factory
from app.models.instrument import Instrument
from app.models.ohlcv import OHLCV


async def get_counts():
    async with async_session_factory() as session:
        i = await session.execute(select(func.count(Instrument.id)))
        o = await session.execute(select(func.count(OHLCV.time)))
        print(f"Instruments: {i.scalar()}")
        print(f"OHLCV: {o.scalar()}")

if __name__ == "__main__":
    asyncio.run(get_counts())
