"""
Application configuration using Pydantic settings.
All configuration is loaded from environment variables with validation.
"""

import secrets
from typing import List, Optional, Union

from pydantic import AnyHttpUrl, field_validator, ValidationInfo
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings with environment variable loading.
    """

    # Application
    APP_NAME: str = "NeuroQuant Gateway"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Unified REST + WebSocket API gateway for NeuroQuant"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    RELOAD: bool = True

    # Security
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "RS256"

    # JWT Keys (RSA)
    JWT_PRIVATE_KEY: Optional[str] = None
    JWT_PUBLIC_KEY: Optional[str] = None

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://neuroquant:neuroquant@localhost:5432/neuroquant"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    DATABASE_POOL_RECYCLE: int = 3600

    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_CACHE_DB: int = 0
    REDIS_PUBSUB_DB: int = 1
    REDIS_SESSIONS_DB: int = 2
    REDIS_DB_CACHE: int = 0
    REDIS_DB_SESSIONS: int = 1
    REDIS_DB_RATE_LIMIT: int = 2
    REDIS_DB_WS: int = 3

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:8000",  # Gateway itself
        "https://neuroquant.app",  # Production domain
    ]

    # Trusted hosts (production)
    ALLOWED_HOSTS: List[str] = ["neuroquant.app", "api.neuroquant.app"]

    # Email
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None

    # Email templates
    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48
    EMAIL_TEMPLATES_DIR: str = "app/email-templates"
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24

    # Security
    FIELD_ENCRYPTION_KEY: str = secrets.token_urlsafe(32)
    TOTP_ISSUER: str = "NeuroQuant"

    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 1000
    RATE_LIMIT_AUTH_REQUESTS_PER_MINUTE: int = 5
    RATE_LIMIT_ML_REQUESTS_PER_HOUR: int = 100
    RATE_LIMIT_WS_CONNECTIONS_PER_USER: int = 10

    # External APIs
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    YAHOO_FINANCE_API_KEY: Optional[str] = None
    NEWS_API_KEY: Optional[str] = None

    # ML Service URLs
    ML_ENGINE_URL: str = "http://localhost:8001"
    DATA_PIPELINE_URL: str = "http://localhost:8002"
    RISK_ENGINE_URL: str = "http://localhost:8003"
    ALERT_SERVICE_URL: str = "http://localhost:8004"
    BACKTESTING_ENGINE_URL: str = "http://localhost:8005"

    # Monitoring
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"

    # Feature flags
    ENABLE_WEBSOCKETS: bool = True
    ENABLE_AUDIT_LOGGING: bool = True
    ENABLE_RATE_LIMITING: bool = True
    ENABLE_CORS: bool = True

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(
        cls, v: Union[str, List[str]]
    ) -> Union[List[str], str]:
        """Parse CORS origins from environment variable."""
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith(("postgresql://", "postgresql+asyncpg://")):
            raise ValueError("Database URL must be a PostgreSQL connection string")
        return v

    @field_validator("REDIS_URL", mode="after")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format."""
        if not v.startswith(("redis://", "rediss://")):
            raise ValueError("Redis URL must start with redis:// or rediss://")
        return v

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()