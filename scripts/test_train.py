import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.database.connection import async_session_factory
from app.services.ml_engine.training_pipeline import TrainingPipeline

async def run():
    # Assuming we have RELIANCE.NS in the db
    pipeline = TrainingPipeline("RELIANCE.NS")
    results = await pipeline.run()
    print(results)

if __name__ == "__main__":
    asyncio.run(run())
