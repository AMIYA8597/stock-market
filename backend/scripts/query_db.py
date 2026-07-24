import asyncio
import sys

sys.path.insert(0, '.')
from sqlalchemy import text

from app.database.connection import async_session_factory


async def r():
    async with async_session_factory() as db:
        res = await db.execute(text('SELECT * FROM model_metric;'))
        print(res.keys())
        print(res.fetchall())

if __name__ == "__main__":
    asyncio.run(r())
