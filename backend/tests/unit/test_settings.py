import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_refusal_to_run_as_postgres_in_prod():
    # Production with postgres user should fail
    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql+asyncpg://postgres:changeme@localhost:5432/db",
            REDIS_URL="redis://localhost",
            UPSTOX_API_KEY="key",
            UPSTOX_API_SECRET="secret"
        )

def test_allow_postgres_in_test():
    # Test environment allows postgres user
    settings = Settings(
        ENVIRONMENT="test",
        DATABASE_URL="postgresql+asyncpg://postgres:changeme@localhost:5432/db",
        REDIS_URL="redis://localhost",
        UPSTOX_API_KEY="key",
        UPSTOX_API_SECRET="secret"
    )
    assert settings.DATABASE_URL == "postgresql+asyncpg://postgres:changeme@localhost:5432/db"

def test_pool_mode_params():
    settings = Settings(DB_POOL_MODE="transaction")
    assert settings.DB_POOL_MODE == "transaction"
