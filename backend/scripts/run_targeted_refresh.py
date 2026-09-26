import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import func, select
from tasks.data_tasks import _process_symbol

from app.database.connection import async_session_factory
from app.models.instrument import Instrument
from app.models.research import Dataset as FeatureVector


async def refresh_targeted():
    async with async_session_factory() as session:
        result = await session.execute(select(Instrument.id).limit(5))
        symbol_ids = result.scalars().all()

    total = 0
    for sid in symbol_ids:
        count = await _process_symbol(sid)
        total += count

    async with async_session_factory() as session:
        result = await session.execute(select(func.count(FeatureVector.time)))
        print(f"Total Feature Vectors: {result.scalar()}")

if __name__ == "__main__":
    asyncio.run(refresh_targeted())
