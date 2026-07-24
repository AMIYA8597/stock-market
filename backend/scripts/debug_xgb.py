import asyncio
import sys

sys.path.insert(0, '.')
from app.services.prediction_engine import get_full_prediction


async def run():
    try:
        await get_full_prediction('RELIANCE.NS', bypass_cache=True)
    except Exception:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run())
