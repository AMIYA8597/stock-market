import asyncio

from sqlalchemy import text

from app.database.connection import get_db


async def run():
    async for db in get_db():
        r = await db.execute(text('SELECT id, symbol_id, model_type, is_active FROM model_artifacts'))
        print(r.fetchall())
        break
asyncio.run(run())
