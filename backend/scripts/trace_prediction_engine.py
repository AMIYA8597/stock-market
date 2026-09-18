import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.services.prediction_engine import get_full_prediction


async def main():
    print("Tracing prediction engine for RELIANCE.NS (bypassing cache)...")

    start_time = time.time()

    try:
        res = await get_full_prediction("RELIANCE.NS", bypass_cache=True)
        end_time = time.time()

        print("\n--- Live Prediction Trace ---")
        print("Target: RELIANCE.NS")
        print(f"End-to-End Time: {end_time - start_time:.3f} seconds")
        print(f"Result type: {type(res)}")
        if isinstance(res, dict):
            print(f"Ensemble Status: {res.get('model_status')}")
            print(f"Overall Direction: {res.get('direction')}")
            print(f"Confidence: {res.get('confidence')}")
            print(f"Target 5d: {res.get('target_price_5d')}")
        else:
            print(f"Result: {res}")
        print("-----------------------------\n")
    except Exception as e:
        print(f"Prediction Engine failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
