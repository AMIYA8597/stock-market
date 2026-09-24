import asyncio
from sqlalchemy import text
from app.database.connection import async_session_factory

async def run():
    async with async_session_factory() as session:
        res = await session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'"))
        tables = [r[0] for r in res]
        
        result = {}
        for table in tables:
            count_res = await session.execute(text(f"SELECT count(*) FROM {table}"))
            result[table] = count_res.scalar()
        
        import json
        print(json.dumps(result, indent=2))

asyncio.run(run())
