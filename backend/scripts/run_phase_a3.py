import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging to see the table output
logging.basicConfig(level=logging.INFO, format='%(message)s')

from app.services.ml_engine.training_pipeline import TrainingPipeline


async def main():
    pipeline = TrainingPipeline("A")
    await pipeline.run()

if __name__ == "__main__":
    asyncio.run(main())
