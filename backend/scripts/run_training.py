import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.ml_engine.training_pipeline import TrainingPipeline


async def main():
    pipeline = TrainingPipeline("RELIANCE.NS")
    await pipeline.run()

if __name__ == "__main__":
    asyncio.run(main())
