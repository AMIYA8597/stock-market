import asyncio
import sys

sys.path.insert(0, '.')
from app.api.v1.predictions import get_prediction_history
from app.database.connection import async_session_factory


async def main():
    async with async_session_factory() as db:
        res = await get_prediction_history("RELIANCE.NS", db)
        print(res)

if __name__ == "__main__":
    asyncio.run(main())
