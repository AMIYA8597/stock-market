import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tasks.retraining_trigger import check_drift_and_retrain

async def main():
    print("Testing real drift calculation for RELIANCE.NS...")
    try:
        await check_drift_and_retrain("RELIANCE.NS")
    except Exception as e:
        print(f"Error checking drift: {e}")

if __name__ == "__main__":
    asyncio.run(main())
