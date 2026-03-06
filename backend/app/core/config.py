"""
Application configuration using Pydantic Settings.

All settings are loaded from environment variables (or .env file).
Secrets must never be hardcoded — they are injected via the environment.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ─── App ───────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    PROJECT_NAME: str = "QuantEdge"
    API_V1_PREFIX: str = "/api/v1"

    # ─── Database ──────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://quantedge:quantedge@db:5432/quantedge"
    DATABASE_URL_SYNC: str = "postgresql://quantedge:quantedge@db:5432/quantedge"

    # ─── Redis ─────────────────────────────────────────────
    REDIS_URL: str = "redis://cache:6379/0"

    # ─── Security / JWT ────────────────────────────────────
    SECRET_KEY: str = "CHANGE_ME_TO_A_RANDOM_64_CHAR_HEX_STRING"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── CORS ──────────────────────────────────────────────
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:80"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return json.loads(v)
        return v

    # ─── Data Source API Keys ──────────────────────────────
    ALPHA_VANTAGE_API_KEY: str = ""
    NEWSAPI_KEY: str = ""
    FRED_API_KEY: str = ""
    COINGECKO_API_KEY: str = ""
    FINNHUB_API_KEY: str = ""

    # ─── Email ─────────────────────────────────────────────
    SENDGRID_API_KEY: str = ""
    SENDGRID_FROM_EMAIL: str = "alerts@quantedge.dev"

    # ─── MLflow ────────────────────────────────────────────
    MLFLOW_TRACKING_URI: str = "http://mlflow:5000"

    # ─── Celery ────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://cache:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://cache:6379/2"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
