from pathlib import Path

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


def test_all_settings_fields_present_in_env_example():
    """Every Settings field must have a matching KEY= line in backend/.env.example.

    This test fails when a developer adds a new Settings field without
    documenting it in .env.example, preventing silent "works locally, breaks
    in a fresh checkout" surprises.
    """
    env_example = Path(__file__).parents[2] / ".env.example"
    assert env_example.exists(), f".env.example not found at {env_example}"

    content = env_example.read_text(encoding="utf-8")
    # Collect all KEY names that appear as KEY= (ignoring comments)
    documented: set[str] = set()
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip().upper()
        if key:
            documented.add(key)

    # Collect all field names from Settings (skip internal pydantic attrs)
    model_fields: set[str] = {name.upper() for name in Settings.model_fields}

    missing = model_fields - documented
    assert not missing, (
        "The following Settings fields are not documented in backend/.env.example.\n"
        "Add them with a sensible default or blank value:\n"
        + "\n".join(f"  {k}=" for k in sorted(missing))
    )
