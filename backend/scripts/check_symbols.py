import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sqlalchemy import select

from app.database.connection import async_session_factory
from app.models.instrument import Instrument


async def get_syms():
    async with async_session_factory() as session:
        res = await session.execute(select(Instrument.symbol).limit(10))
        print(res.scalars().all())

if __name__ == "__main__":
    asyncio.run(get_syms())
