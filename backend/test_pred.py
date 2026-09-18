
import asyncio

from app.services.prediction_engine import get_full_prediction


async def test():
    try:
        res = await get_full_prediction('RELIANCE.NS', bypass_cache=True)
        print('SUCCESS:', res['forecast'])
    except Exception as e:
        print('ERROR:', e)
asyncio.run(test())
