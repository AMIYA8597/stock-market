import asyncio
from sqlalchemy import text
from app.database.connection import async_session_factory

async def test_rls():
    async with async_session_factory() as session:
        # Become system
        await session.execute(text("SELECT set_config('app.is_system', 'true', true)"))
        # Insert
        try:
            await session.execute(text("INSERT INTO users (id, email, auth_id, status, email_verified, created_at, updated_at) VALUES ('11111111-1111-1111-1111-111111111111', 'a@b.c', '111', 'active', true, now(), now()) ON CONFLICT DO NOTHING"))
            print("Inserted user 1 with system bypass")
        except Exception as e:
            print("Failed insert system:", e)
            
        # Unset system
        await session.execute(text("SELECT set_config('app.is_system', '', true)"))

        # Try inserting without system (should fail)
        try:
            await session.execute(text("INSERT INTO users (id, email, auth_id, status, email_verified, created_at, updated_at) VALUES ('22222222-2222-2222-2222-222222222222', 'b@c.d', '222', 'active', true, now(), now()) ON CONFLICT DO NOTHING"))
            print("Inserted user 2 without bypass?!")
        except Exception as e:
            print("Failed insert normal:", e)

asyncio.run(test_rls())
