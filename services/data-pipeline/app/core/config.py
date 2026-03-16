"""Configuration for Data Pipeline Service."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Data pipeline settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://neuroquant:neuroquant@localhost:5432/neuroquant"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Service
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Data sources
    YFINANCE_TIMEOUT: int = 30
    MAX_CONCURRENT_FETCHES: int = 10


settings = Settings()