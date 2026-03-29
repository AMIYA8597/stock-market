"""
Application configuration using Pydantic Settings v2.

All settings are loaded from environment variables (or .env file).
Secrets must never be hardcoded — they are injected via the environment.

Production deployment uses 12-factor app methodology:
https://12factor.net/
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings loaded from environment variables.
    
    All configuration is read from the environment or .env file.
    Environment variables take precedence over .env values.
    
    Args:
        None: Settings are automatically loaded from environment.
        
    Returns:
        Settings: Singleton instance with all validated settings.
        
    Raises:
        ValidationError: If required environment variables are missing or invalid.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.example"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ──────────────────────────────────────────────────────
    ENVIRONMENT: str = Field(
        default="development",
        description="Deployment environment: development, staging, production"
    )
    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode (SQLAlchemy echo, verbose logging)"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )
    PROJECT_NAME: str = Field(
        default="NeuroQuant",
        description="Application name for logs and metrics"
    )
    API_V1_PREFIX: str = Field(
        default="/api/v1",
        description="Base path for all API v1 endpoints"
    )

    # ─── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://neuroquant:changeme@localhost:5432/neuroquant_db",
        description="Async PostgreSQL database URL (asyncpg driver)"
    )
    DATABASE_POOL_SIZE: int = Field(
        default=20,
        description="SQLAlchemy connection pool size"
    )
    DATABASE_MAX_OVERFLOW: int = Field(
        default=10,
        description="Maximum connections to overflow beyond pool_size"
    )
    DATABASE_POOL_RECYCLE: int = Field(
        default=3600,
        description="Recycle connections after N seconds (for connection pooling)"
    )

    # ─── Redis ────────────────────────────────────────────────────────────
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching and session storage"
    )
    REDIS_MAX_CONNECTIONS: int = Field(
        default=50,
        description="Maximum Redis connection pool size"
    )

    # ─── Security / JWT (RS256) ───────────────────────────────────────────
    JWT_PRIVATE_KEY_PATH: str = Field(
        default="./keys/private.pem",
        description="Path to RSA private key for JWT signing"
    )
    JWT_PUBLIC_KEY_PATH: str = Field(
        default="./keys/public.pem",
        description="Path to RSA public key for JWT verification"
    )
    JWT_ALGORITHM: str = Field(
        default="RS256",
        description="JWT signing algorithm (RS256 for RSA)"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=15,
        description="Access token expiration time in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="Refresh token expiration time in days"
    )
    TOKEN_BLACKLIST_ENABLED: bool = Field(
        default=True,
        description="Enable JWT token blacklist on logout"
    )

    # ─── Password Security ─────────────────────────────────────────────────
    PASSWORD_MIN_LENGTH: int = Field(
        default=12,
        description="Minimum password length"
    )
    PASSWORD_REQUIRE_UPPERCASE: bool = Field(
        default=True,
        description="Require at least one uppercase letter"
    )
    PASSWORD_REQUIRE_NUMBERS: bool = Field(
        default=True,
        description="Require at least one number"
    )
    PASSWORD_REQUIRE_SPECIAL: bool = Field(
        default=True,
        description="Require at least one special character"
    )
    PASSWORD_HASH_ALGORITHM: str = Field(
        default="argon2",
        description="Password hashing algorithm: argon2, bcrypt"
    )

    # ─── Field Encryption (Fernet) ────────────────────────────────────────
    FIELD_ENCRYPTION_KEY: str = Field(
        default="",
        description="Fernet encryption key (base64 encoded) for sensitive fields"
    )
    ENCRYPTION_ENABLED: bool = Field(
        default=False,
        description="Enable field-level encryption for sensitive data"
    )

    # ─── CORS ─────────────────────────────────────────────────────────────
    BACKEND_CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        description="List of allowed CORS origins (comma-separated or JSON array)"
    )
    CORS_ALLOW_METHODS: list[str] = Field(
        default=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        description="Allowed CORS HTTP methods"
    )
    CORS_ALLOW_HEADERS: list[str] = Field(
        default=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key", "Stripe-Signature"],
        description="Allowed CORS headers"
    )
    ALLOWED_HOSTS: list[str] = Field(
        default=["localhost", "127.0.0.1"],
        description="Trusted hosts for Host header validation"
    )
    SECURITY_CSP_POLICY: str = Field(
        default="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https: wss:; font-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        description="Content-Security-Policy header value"
    )

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Convert comma-separated string or JSON array to list."""
        if isinstance(v, str):
            if v.startswith("["):
                return json.loads(v)
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("CORS_ALLOW_METHODS", "CORS_ALLOW_HEADERS", "ALLOWED_HOSTS", mode="before")
    @classmethod
    def assemble_string_list(cls, v: str | list[str]) -> list[str]:
        """Convert comma-separated string or JSON array to list."""
        if isinstance(v, str):
            if v.startswith("["):
                return json.loads(v)
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @field_validator("DEBUG", mode="before")
    @classmethod
    def coerce_debug_flag(cls, v: Any) -> bool:
        """Accept common boolean-ish env values and degrade safely to False."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug"}:
                return True
            if normalized in {
                "0",
                "false",
                "no",
                "off",
                "warn",
                "warning",
                "info",
                "error",
                "critical",
            }:
                return False
        return False

    # ─── Data Source API Keys ─────────────────────────────────────────────
    ALPHA_VANTAGE_API_KEY: str = Field(
        default="",
        description="Alpha Vantage API key for stock data"
    )
    NEWSAPI_KEY: str = Field(
        default="",
        description="NewsAPI key for financial news data"
    )
    FRED_API_KEY: str = Field(
        default="",
        description="FRED API key for macroeconomic data"
    )
    COINGECKO_API_KEY: str = Field(
        default="",
        description="CoinGecko API key for cryptocurrency data"
    )
    FINNHUB_API_KEY: str = Field(
        default="",
        description="Finnhub API key for intraday and company data"
    )

    # ─── Email / Notifications ────────────────────────────────────────────
    SENDGRID_API_KEY: str = Field(
        default="",
        description="SendGrid API key for email notifications"
    )
    SENDGRID_FROM_EMAIL: str = Field(
        default="alerts@neuroquant.local",
        description="From address for SendGrid emails"
    )
    ALERT_EMAIL_ENABLED: bool = Field(
        default=False,
        description="Enable email alerts"
    )

    # ─── ML & Model Settings ──────────────────────────────────────────────
    MODEL_CHECKPOINT_DIR: str = Field(
        default="./data/models",
        description="Directory for storing trained model checkpoints"
    )
    ENABLE_GPU: bool = Field(
        default=True,
        description="Enable GPU acceleration for PyTorch models"
    )
    INFERENCE_BATCH_SIZE: int = Field(
        default=32,
        description="Batch size for model inference"
    )
    TRAINING_BATCH_SIZE: int = Field(
        default=64,
        description="Batch size for model training"
    )
    SEQUENCE_LENGTH: int = Field(
        default=60,
        description="Number of historical timesteps for feature vectors"
    )
    FORECAST_HORIZON: int = Field(
        default=5,
        description="Number of days ahead to forecast"
    )

    # ─── Feature Engineering ──────────────────────────────────────────────
    FEATURE_NORMALIZATION_METHOD: str = Field(
        default="robust",
        description="Feature scaling method: robust, standard, minmax"
    )
    FEATURE_CACHE_TTL_HOURS: int = Field(
        default=24,
        description="Time-to-live for cached feature vectors in hours"
    )

    # ─── Online Learning & Drift Detection ────────────────────────────────
    ONLINE_LEARNING_ENABLED: bool = Field(
        default=True,
        description="Enable online learning for concept drift adaptation"
    )
    DRIFT_DETECTION_ENABLED: bool = Field(
        default=True,
        description="Enable concept drift detection (ADWIN algorithm)"
    )
    DRIFT_DETECTION_ALPHA: float = Field(
        default=0.002,
        description="ADWIN drift detection sensitivity (0.001-0.1)"
    )
    RETRAIN_MIN_INTERVAL_HOURS: int = Field(
        default=24,
        description="Minimum hours between scheduled model retrains"
    )
    RETRAIN_SAMPLE_SIZE: int = Field(
        default=500,
        description="Number of recent samples for online fine-tuning"
    )

    # ─── Backtesting ──────────────────────────────────────────────────────
    BACKTEST_CACHE_DIR: str = Field(
        default="./data/backtest_cache",
        description="Directory for caching backtest results"
    )
    BACKTEST_MAX_WORKERS: int = Field(
        default=4,
        description="Maximum parallel backtest workers"
    )

    # ─── Celery Task Queue ────────────────────────────────────────────────
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        description="Celery message broker URL (Redis)"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2",
        description="Celery result backend URL (Redis)"
    )
    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(
        default=600,
        description="Soft time limit for Celery tasks in seconds"
    )
    CELERY_TASK_HARD_TIME_LIMIT: int = Field(
        default=900,
        description="Hard time limit for Celery tasks in seconds"
    )

    # ─── Monitoring & MLflow ──────────────────────────────────────────────
    MLFLOW_TRACKING_URI: str = Field(
        default="http://localhost:5000",
        description="MLflow tracking server URI"
    )
    MLFLOW_EXPERIMENT_NAME: str = Field(
        default="neuroquant-prod",
        description="MLflow experiment name for model tracking"
    )
    ENABLE_PROMETHEUS_METRICS: bool = Field(
        default=True,
        description="Enable Prometheus metrics collection"
    )
    METRICS_COLLECTION_INTERVAL_SECONDS: int = Field(
        default=60,
        description="Interval for collecting performance metrics"
    )

    # ─── Frontend URLs ────────────────────────────────────────────────────
    FRONTEND_URL: str = Field(
        default="http://localhost:3000",
        description="Frontend application URL for redirects and CORS"
    )
    FRONTEND_STAGING_URL: str = Field(
        default="https://staging.neuroquant.dev",
        description="Staging frontend URL"
    )
    FRONTEND_PRODUCTION_URL: str = Field(
        default="https://app.neuroquant.com",
        description="Production frontend URL"
    )

    # ─── Billing & Email Security ───────────────────────────────────────
    PAYMENT_WEBHOOK_SECRET: str = Field(
        default="",
        description="Shared secret for payment webhook signature validation"
    )
    PAYMENT_WEBHOOK_TOLERANCE_SECONDS: int = Field(
        default=300,
        description="Allowed age (seconds) for payment webhook signatures"
    )
    SENTRY_DSN: str = Field(
        default="",
        description="Sentry DSN for production error tracking"
    )
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Password reset token validity window in minutes"
    )

    # ─── WebSocket ────────────────────────────────────────────────────────
    WEBSOCKET_HEARTBEAT_INTERVAL: int = Field(
        default=30,
        description="WebSocket heartbeat interval in seconds"
    )
    WEBSOCKET_MAX_CONNECTIONS_PER_USER: int = Field(
        default=5,
        description="Maximum concurrent WebSocket connections per user"
    )

    # ─── Rate Limiting ────────────────────────────────────────────────────
    RATE_LIMIT_ENABLED: bool = Field(
        default=True,
        description="Enable rate limiting on API endpoints"
    )
    DEFAULT_RATE_LIMIT: str = Field(
        default="100/minute",
        description="Default rate limit (requests/time_window)"
    )
    AUTH_RATE_LIMIT: str = Field(
        default="10/minute",
        description="Rate limit specifically for authentication endpoints"
    )
    PREMIUM_RATE_LIMIT: str = Field(
        default="1000/minute",
        description="Rate limit for premium tier users"
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"

    @property
    def jwt_private_key_path(self) -> Path:
        """Get Path object for JWT private key."""
        return Path(self.JWT_PRIVATE_KEY_PATH)

    @property
    def jwt_public_key_path(self) -> Path:
        """Get Path object for JWT public key."""
        return Path(self.JWT_PUBLIC_KEY_PATH)

    @property
    def model_checkpoint_path(self) -> Path:
        """Get Path object for model checkpoint directory."""
        return Path(self.MODEL_CHECKPOINT_DIR)


# ─── Singleton Getter ──────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton.
    
    Uses functools.lru_cache to ensure only one Settings instance
    is created and reused throughout the application lifetime.
    
    Returns:
        Settings: The global settings instance.
    """
    return Settings()
