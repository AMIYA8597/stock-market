import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.connection import engine
from app.models.regime_states import RegimeState


async def create():
    async with engine.begin() as conn:
        await conn.run_sync(RegimeState.__table__.create)

if __name__ == "__main__":
    asyncio.run(create())
