"""Shared real-database test client for auth-lifecycle tests.

The top-level tests/conftest.py `client`/`db` fixtures back onto a
hand-written DummySession that only recognizes a few hardcoded query shapes
(users, refresh_sessions) - it has no concept of the email_otps table, so it
can't exercise the real register -> verify-OTP -> login lifecycle. This
fixture spins up a real (in-memory) SQLite engine instead, exactly like
tests/integration/test_repository.py's `real_db`, but wired through the ASGI
app via dependency override (StaticPool, so every request-scoped session the
FastAPI dependency hands out shares the same in-memory database).
"""

from __future__ import annotations

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.dependencies import get_db
from app.core.test_state import reset_test_state
from app.database.connection import Base
from app.main import app


@pytest_asyncio.fixture
async def auth_client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # get_current_context() sets a Postgres RLS session variable via
    # set_config(...) on every authenticated request. That function doesn't
    # exist on SQLite; registering a no-op stand-in lets the same real
    # request path run against this real-but-lightweight test database
    # without needing a Postgres server for these tests.
    @event.listens_for(engine.sync_engine, "connect")
    def _register_set_config(dbapi_connection, _record):
        dbapi_connection.create_function("set_config", 3, lambda *_args: None)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    reset_test_state()
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        yield client
    app.dependency_overrides.pop(get_db, None)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    reset_test_state()
