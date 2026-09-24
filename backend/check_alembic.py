import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import get_settings
async def main():
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT * FROM alembic_version"))
        print(res.fetchall())
        res = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='users'"))
        print([r[0] for r in res.fetchall()])
    await engine.dispose()
asyncio.run(main())
