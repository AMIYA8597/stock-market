import asyncio
import json
import logging

from app.services.prediction_engine import get_full_prediction

logging.basicConfig(level=logging.INFO)

async def run():
    # Use RELIANCE.NS for data, but point artifact_path to the existing A model
    # The expected features are the same across models.
    res = await get_full_prediction(
        "RELIANCE.NS",
        bypass_cache=True,
        artifact_path="D:/work/stock-market/backend/data/artifacts/xgboost_A_6d8d915f.pkl"
    )
    print("\n--- END-TO-END PREDICTION TRACE ---")
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    asyncio.run(run())
