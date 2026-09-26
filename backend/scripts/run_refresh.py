import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import func, select
from tasks.data_tasks import refresh_features

from app.database.connection import async_session_factory
from app.models.research import Dataset as FeatureVector


async def count_features():
    async with async_session_factory() as session:
        result = await session.execute(select(func.count(FeatureVector.time)))
        print(f"Total Feature Vectors: {result.scalar()}")

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.ERROR)
    print("Running refresh_features...")
    res = refresh_features()
    print("Result:", res)
    asyncio.run(count_features())
