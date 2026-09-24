import asyncio
from sqlalchemy import text
from app.database.connection import async_session_factory, engine

async def setup_roles():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("CREATE ROLE nq_api WITH LOGIN PASSWORD 'nq_api_secret';"))
            print("Role nq_api created.")
        except Exception as e:
            print("Role might already exist:", e)
            
        await conn.execute(text("GRANT USAGE ON SCHEMA public TO nq_api;"))
        await conn.execute(text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO nq_api;"))
        await conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO nq_api;"))
        await conn.execute(text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO nq_api;"))
        await conn.execute(text("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO nq_api;"))
        print("Grants applied.")

asyncio.run(setup_roles())
