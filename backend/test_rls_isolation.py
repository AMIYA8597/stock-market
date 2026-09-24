import asyncio
from sqlalchemy import text
from app.database.connection import engine, async_session_factory

async def test_rls():
    # Setup - use engine to bypass RLS for inserting
    async with engine.begin() as conn:
        try:
            await conn.execute(text("INSERT INTO users (id, email, auth_id, status, email_verified, created_at, updated_at) VALUES ('11111111-1111-1111-1111-111111111111', 'a@b.c', '111', 'active', true, now(), now()) ON CONFLICT DO NOTHING"))
            await conn.execute(text("INSERT INTO users (id, email, auth_id, status, email_verified, created_at, updated_at) VALUES ('22222222-2222-2222-2222-222222222222', 'b@c.d', '222', 'active', true, now(), now()) ON CONFLICT DO NOTHING"))
        except Exception as e:
            print("Failed inserting setup users:", e)

    # Test
    async with async_session_factory() as session:
        try:
            res = await session.execute(text("SELECT id FROM users"))
            print(f"Users without RLS config (expect 0 if RLS active): {len(res.fetchall())}")
        except Exception as e:
            print(f"Error without RLS config: {e}")
            
        # Now set config
        await session.execute(text("SELECT set_config('request.jwt.claim.sub', '11111111-1111-1111-1111-111111111111', true)"))
        
        res = await session.execute(text("SELECT id FROM users"))
        print(f"Users with RLS config for user 1 (expect 1): {len(res.fetchall())}")

asyncio.run(test_rls())
