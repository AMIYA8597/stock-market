import asyncio
from sqlalchemy import text
from app.core.database import async_session_factory

async def run():
    async with async_session_factory() as session:
        res = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        print([r[0] for r in res])

asyncio.run(run())
