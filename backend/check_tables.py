import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import get_settings
async def main():
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
        print([r[0] for r in res.fetchall()])
    await engine.dispose()
asyncio.run(main())
