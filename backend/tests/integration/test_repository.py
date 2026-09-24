from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.connection import Base
from app.models.identity import User
from app.repositories.user import UserRepository

pytestmark = pytest.mark.anyio


@pytest.fixture
async def real_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(
        autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
    )

    async with SessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def test_user_repository_round_trip(real_db: AsyncSession):
    repo = UserRepository(real_db)

    # Create user
    user = User(
        email=f"repo_test_{uuid4().hex[:8]}@example.com",
        full_name="Repo Test",
    )
    repo.add(user)
    await real_db.commit()

    # Get by ID
    fetched = await repo.get(user.id)
    assert fetched is not None
    assert fetched.email == user.email

    # Get by email
    fetched_by_email = await repo.get_by_email(user.email)
    assert fetched_by_email is not None
    assert fetched_by_email.id == user.id

    # Delete
    await repo.delete(fetched)
    await real_db.commit()

    # Verify deletion
    deleted = await repo.get(user.id)
    assert deleted is None
