import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.features.feature_pipeline import fetch_and_prepare_data
from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.instrument import Instrument
from app.models.model_artifact import ModelArtifact
from app.services.prediction_engine import build_ensemble_signal


async def main():
    symbol = "RELIANCE.NS"
    print("Fetching data...")
    df = await fetch_and_prepare_data(symbol)

    print("Fetching artifact...")
    async with async_session_factory() as session:
        stmt = select(ModelArtifact).join(Instrument).where(Instrument.symbol == symbol, ModelArtifact.model_type == "XGBoost", ModelArtifact.is_active)
        art = (await session.execute(stmt)).scalar_one_or_none()
        if not art:
            print("No artifact found!")
            return

        print("Calling build_ensemble_signal...")
        try:
            ensemble = await build_ensemble_signal(symbol, df, art.artifact_path, art.version_tag)
            print("Ensemble result:")
            print(ensemble)
        except Exception as e:
            print(f"Exception caught: {e}")

if __name__ == "__main__":
    asyncio.run(main())
