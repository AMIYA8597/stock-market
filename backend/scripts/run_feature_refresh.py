import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select

from app.database.connection import async_session_factory
from app.models.feature_vectors import FeatureVector
from app.models.instrument import Instrument
from tasks.data_tasks import _refresh_features_async


async def run_features():
    print("Starting feature refresh...")
    await _refresh_features_async()
    print("Feature refresh complete.")

    async with async_session_factory() as session:
        # Check one of the symbols (e.g. symbol_id 1)
        stmt = select(FeatureVector, Instrument.symbol).outerjoin(Instrument).limit(1)
        result = await session.execute(stmt)
        row = result.first()
        if row:
            vector, symbol = row
            print(f"\n--- SAMPLE FEATURE VECTOR for {symbol} ---")
            print(f"Date: {vector.time}")
            f = vector.features
            print(f"Sentiment Score: {f.get('sentiment_score')}")
            print(f"Market Sentiment Index: {f.get('market_sentiment_index')}")
            print(f"Regime State: {f.get('regime_state')}")
            print(f"Regime Vol: {f.get('regime_cond_vol')}")
            print(f"Market Regime State: {f.get('market_regime_state')}")
            print(f"Market Regime Vol: {f.get('market_regime_cond_vol')}")

if __name__ == "__main__":
    asyncio.run(run_features())
