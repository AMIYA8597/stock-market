import asyncio

from sqlalchemy import func, select

from app.database.connection import async_session_factory
from app.models.feature_vectors import FeatureVector
from app.models.instrument import Instrument
from app.tasks.feature_tasks import _build_feature_vectors_async


async def main():
    async with async_session_factory() as session:
        res = await session.execute(select(Instrument.symbol))
        symbols = res.scalars().all()

    print(f"Building features for {len(symbols)} symbols...")

    total_features = 0
    for sym in symbols:
        res = await _build_feature_vectors_async(sym)
        if res.get("status") == "success":
            total_features += res.get("count", 0)

    print(f"Total features built and inserted: {total_features}")

    # Verify DB count
    async with async_session_factory() as session:
        res = await session.execute(select(func.count(FeatureVector.time)))
        db_count = res.scalar()
        print(f"Total records in feature_vectors table: {db_count}")

if __name__ == "__main__":
    asyncio.run(main())
