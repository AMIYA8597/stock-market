import asyncio
from app.core.database import async_session_factory
from app.schemas.auth import UserRegister
from app.api.v1.auth import register

async def test():
    async with async_session_factory() as db:
        try:
            req = UserRegister(email='test_crash7@a.com', password='Password123!', full_name='Crash')
            await register(req, db)
            print("SUCCESS!")
        except Exception as e:
            import traceback
            traceback.print_exc()

asyncio.run(test())
