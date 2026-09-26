import asyncio
import logging

logger = logging.getLogger("run_walk_forward")

async def main():
    logger.info("run_walk_forward.py is now a deprecated wrapper.")
    logger.info("Please use backend/app/services/ml_engine/training_pipeline.py for the canonical walk-forward research engine.")
    # In a full implementation, we would invoke the TrainingPipeline here
    # against canonical datasets, rather than directly scraping yfinance.
    logger.info("Walk-forward engine execution has been migrated to the canonical pipeline.")

if __name__ == "__main__":
    asyncio.run(main())
