"""
Application configuration using Pydantic Settings v2.

All settings are loaded from environment variables (or .env file).
Secrets must never be embedded — they are injected via the environment.

Production deployment uses 12-factor app methodology:
https://12factor.net/
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ──────────────────────────────────────────────────────
    ENVIRONMENT: str = Field(
        default="development",
        description="Deployment environment: development, staging, production",
    )
    DEBUG: bool = Field(
        default=False, description="Enable debug mode (SQLAlchemy echo, verbose logging)"
    )
    LOG_LEVEL: str = Field(
        default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL"
    )
    PROJECT_NAME: str = Field(
        default="NeuroQuant", description="Application name for logs and metrics"
    )
    API_V1_PREFIX: str = Field(default="/api/v1", description="Base path for all API v1 endpoints")

    # ─── Database ─────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="",
        description="Runtime DB URL for API (role nq_api)",
    )
    MIGRATIONS_DATABASE_URL: str = Field(
        default="", description="DB URL for Alembic migrations (role nq_migrator)"
    )
    INGEST_DATABASE_URL: str = Field(
        default="", description="DB URL for market data jobs (role nq_ingest)"
    )
    DB_POOL_MODE: str = Field(
        default="session", description="Connection pool mode: 'session' or 'transaction'"
    )
    DB_POOL_SIZE: int = Field(default=5, description="SQLAlchemy connection pool size")
    DB_MAX_OVERFLOW: int = Field(
        default=2, description="Maximum connections to overflow"
    )
    DB_POOL_RECYCLE: int = Field(
        default=1800, description="Recycle connections after N seconds"
    )
    DB_SSL_REQUIRED: bool = Field(default=True, description="Require SSL for DB connection")

    # ─── Redis ────────────────────────────────────────────────────────────
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching and session storage",
    )
    REDIS_MAX_CONNECTIONS: int = Field(default=50, description="Maximum Redis connection pool size")

    # ─── Supabase / Authentication ────────────────────────────────────────
    SUPABASE_URL: str = Field(
        default="", description="Supabase project URL"
    )
    SUPABASE_JWT_SECRET: str = Field(
        default="", description="Supabase JWT secret for token verification"
    )
    SUPABASE_SECRET_KEY: str = Field(
        default="", description="Supabase service role secret key (use with caution)"
    )
    # Note: local RSA JWT keys have been deprecated in favor of Supabase JWTs
    TOKEN_BLACKLIST_ENABLED: bool = Field(
        default=True, description="Enable JWT token blacklist on logout"
    )

    # ─── Password Security ─────────────────────────────────────────────────
    PASSWORD_MIN_LENGTH: int = Field(default=12, description="Minimum password length")
    PASSWORD_REQUIRE_UPPERCASE: bool = Field(
        default=True, description="Require at least one uppercase letter"
    )
    PASSWORD_REQUIRE_NUMBERS: bool = Field(default=True, description="Require at least one number")
    PASSWORD_REQUIRE_SPECIAL: bool = Field(
        default=True, description="Require at least one special character"
    )
    PASSWORD_HASH_ALGORITHM: str = Field(
        default="argon2", description="Password hashing algorithm: argon2, bcrypt"
    )

    # ─── Field Encryption (Fernet) ────────────────────────────────────────
    FIELD_ENCRYPTION_KEY: str = Field(
        default="", description="Fernet encryption key (base64 encoded) for sensitive fields"
    )
    ENCRYPTION_ENABLED: bool = Field(
        default=False, description="Enable field-level encryption for sensitive data"
    )

    # ─── CORS ─────────────────────────────────────────────────────────────
    # NoDecode: these accept a plain comma-separated string (see the
    # "before" validators below) as well as a JSON array. Without NoDecode,
    # pydantic-settings tries to json.loads() any list[str] field's raw env
    # value *before* our validator runs, which raises SettingsError for any
    # non-JSON comma-separated value -- exactly the format .env.example
    # documents and real deployments use (e.g. ALLOWED_HOSTS=a.com,b.com).
    BACKEND_CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "https://neuroquant-sm.vercel.app",
        ],
        description="List of allowed CORS origins (comma-separated or JSON array)",
    )
    CORS_ALLOW_METHODS: Annotated[list[str], NoDecode] = Field(
        default=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        description="Allowed CORS HTTP methods",
    )
    CORS_ALLOW_HEADERS: Annotated[list[str], NoDecode] = Field(
        default=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-Organization-ID",
            "X-API-Key",
            "Idempotency-Key",
            "Stripe-Signature",
        ],
        description="Allowed CORS headers",
    )
    ALLOWED_HOSTS: Annotated[list[str], NoDecode] = Field(
        default=[], description="Trusted hosts for Host header validation"
    )
    SECURITY_CSP_POLICY: str = Field(
        default="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self' https: wss:; font-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        description="Content-Security-Policy header value",
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
        default="", description="Alpha Vantage API key for stock data"
    )
    NEWSAPI_KEY: str = Field(default="", description="NewsAPI key for financial news data")
    FRED_API_KEY: str = Field(default="", description="FRED API key for macroeconomic data")
    COINGECKO_API_KEY: str = Field(
        default="", description="CoinGecko API key for cryptocurrency data"
    )
    FINNHUB_API_KEY: str = Field(
        default="", description="Finnhub API key for intraday and company data"
    )
    # Angel One SmartAPI credentials (free tier)
    ANGEL_ONE_CLIENT_ID: str = Field(default="", description="Angel One SmartAPI client ID")
    ANGEL_ONE_CLIENT_SECRET: str = Field(default="", description="Angel One SmartAPI client secret")
    ANGEL_ONE_TOTP_SECRET: str = Field(
        default="", description="Base32 TOTP secret for Angel One login"
    )

    # ─── Upstox Integration (OAuth / trading) ──────────────────────────────
    UPSTOX_API_KEY: str = Field(default="", description="Upstox API Client ID (API Key)")
    UPSTOX_API_SECRET: str = Field(default="", description="Upstox API Client Secret")
    UPSTOX_REDIRECT_URI: str = Field(
        default="http://localhost:8000/api/v1/auth/upstox/callback",
        description="Upstox Redirect URI for OAuth login",
    )
    UPSTOX_MAX_ORDER_VALUE: float = Field(
        default=10000.0,
        description="Hard server-side risk cap limit on per-order value in INR (e.g. ₹10,000)",
    )

    # ─── Upstox Integration (free read-only Analytics Token, market data) ──
    # A separate credential from UPSTOX_API_KEY/SECRET above: the Analytics
    # Token (Upstox Developer -> Analytics) is free, read-only, valid one
    # year, and covers Market Quote / Historical Data / WebSocket - it
    # cannot place or modify orders, unlike the OAuth flow above which is
    # for the (currently unused, paper-trading-only) broker integration.
    UPSTOX_ANALYTICS_TOKEN: str = Field(
        default="", description="Upstox free read-only Analytics Token for market data"
    )
    UPSTOX_ENABLED: bool = Field(
        default=False, description="Enable the Upstox market data provider"
    )
    UPSTOX_BASE_URL: str = Field(
        default="https://api.upstox.com", description="Upstox REST API base URL"
    )
    UPSTOX_WS_ENABLED: bool = Field(
        default=False, description="Enable the Upstox real-time WebSocket feed"
    )
    UPSTOX_WS_MODE: str = Field(
        default="full",
        description="Upstox WebSocket feed mode: ltpc | full | option_greeks | full_d30",
    )

    # ─── Email / Notifications ────────────────────────────────────────────
    SENDGRID_API_KEY: str = Field(
        default="", description="SendGrid API key for email notifications"
    )
    SENDGRID_FROM_EMAIL: str = Field(
        default="alerts@neuroquant.local", description="From address for SendGrid emails"
    )
    ALERT_EMAIL_ENABLED: bool = Field(default=False, description="Enable email alerts")

    # ─── Auth security (OTP + brute-force lockout) ────────────────────────
    OTP_LENGTH: int = Field(default=6, description="Number of digits in email OTP codes")
    OTP_EXPIRE_MINUTES: int = Field(
        default=10, description="Minutes an email OTP remains valid before expiring"
    )
    OTP_MAX_ATTEMPTS: int = Field(
        default=5, description="Max wrong-OTP attempts before the code is invalidated"
    )
    OTP_RESEND_COOLDOWN_SECONDS: int = Field(
        default=60, description="Minimum seconds between OTP resend requests for the same email"
    )
    LOGIN_MAX_FAILED_ATTEMPTS: int = Field(
        default=5, description="Failed password attempts before an account is temporarily locked"
    )
    LOGIN_LOCKOUT_MINUTES: int = Field(
        default=15, description="Minutes an account stays locked after too many failed logins"
    )
    PASSWORD_MIN_LENGTH: int = Field(
        default=12, description="Minimum password length enforced server-side at registration/reset"
    )

    # ─── ML & Model Settings ──────────────────────────────────────────────
    MODEL_CHECKPOINT_DIR: str = Field(
        default="./data/models", description="Directory for storing trained model checkpoints"
    )
    ENABLE_GPU: bool = Field(default=True, description="Enable GPU acceleration for PyTorch models")
    INFERENCE_BATCH_SIZE: int = Field(default=32, description="Batch size for model inference")
    TRAINING_BATCH_SIZE: int = Field(default=64, description="Batch size for model training")
    SEQUENCE_LENGTH: int = Field(
        default=60, description="Number of historical timesteps for feature vectors"
    )
    FORECAST_HORIZON: int = Field(default=5, description="Number of days ahead to forecast")

    # ─── Live Data ────────────────────────────────────────────────────────
    LIVE_DATA_PROVIDER: str = Field(default="yfinance", description="Default live data provider")
    LIVE_DATA_YFINANCE_RATE_LIMIT: int = Field(
        default=5, description="Requests per minute for yfinance (if applicable)"
    )
    LIVE_DATA_ALPHA_VANTAGE_RATE_LIMIT: int = Field(
        default=5, description="Requests per minute for Alpha Vantage"
    )

    # ─── Feature Engineering ──────────────────────────────────────────────
    FEATURE_NORMALIZATION_METHOD: str = Field(
        default="robust", description="Feature scaling method: robust, standard, minmax"
    )
    FEATURE_CACHE_TTL_HOURS: int = Field(
        default=24, description="Time-to-live for cached feature vectors in hours"
    )

    # ─── Online Learning & Drift Detection ────────────────────────────────
    ONLINE_LEARNING_ENABLED: bool = Field(
        default=True, description="Enable online learning for concept drift adaptation"
    )
    DRIFT_DETECTION_ENABLED: bool = Field(
        default=True, description="Enable concept drift detection (ADWIN algorithm)"
    )
    DRIFT_DETECTION_ALPHA: float = Field(
        default=0.002, description="ADWIN drift detection sensitivity (0.001-0.1)"
    )
    RETRAIN_MIN_INTERVAL_HOURS: int = Field(
        default=24, description="Minimum hours between scheduled model retrains"
    )
    RETRAIN_SAMPLE_SIZE: int = Field(
        default=500, description="Number of recent samples for online fine-tuning"
    )

    # ─── Backtesting ──────────────────────────────────────────────────────
    BACKTEST_CACHE_DIR: str = Field(
        default="./data/backtest_cache", description="Directory for caching backtest results"
    )
    BACKTEST_MAX_WORKERS: int = Field(default=4, description="Maximum parallel backtest workers")

    # ─── Celery Task Queue ────────────────────────────────────────────────
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1", description="Celery message broker URL (Redis)"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2", description="Celery result backend URL (Redis)"
    )
    CELERY_TASK_SOFT_TIME_LIMIT: int = Field(
        default=600, description="Soft time limit for Celery tasks in seconds"
    )
    CELERY_TASK_HARD_TIME_LIMIT: int = Field(
        default=900, description="Hard time limit for Celery tasks in seconds"
    )

    # ─── Monitoring & MLflow ──────────────────────────────────────────────
    MLFLOW_TRACKING_URI: str = Field(
        default="http://localhost:5000", description="MLflow tracking server URI"
    )
    MLFLOW_EXPERIMENT_NAME: str = Field(
        default="neuroquant-prod", description="MLflow experiment name for model tracking"
    )
    ENABLE_PROMETHEUS_METRICS: bool = Field(
        default=True, description="Enable Prometheus metrics collection"
    )
    METRICS_COLLECTION_INTERVAL_SECONDS: int = Field(
        default=60, description="Interval for collecting performance metrics"
    )

    # ─── Frontend URLs ────────────────────────────────────────────────────
    FRONTEND_URL: str = Field(
        default="http://localhost:3000",
        description="Frontend application URL for redirects and CORS",
    )
    FRONTEND_STAGING_URL: str = Field(
        default="https://staging.neuroquant.dev", description="Staging frontend URL"
    )
    FRONTEND_PRODUCTION_URL: str = Field(
        default="https://app.neuroquant.com", description="Production frontend URL"
    )

    # ─── Billing & Email Security ───────────────────────────────────────
    SENTRY_DSN: str = Field(default="", description="Sentry DSN for production error tracking")
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Password reset token validity window in minutes"
    )
    # Must NOT match the shape of a real Razorpay key id (rzp_live_.../rzp_test_...)
    # so it can never be mistaken for one, but must still contain "replace_me"
    # so app/api/v1/payments.py::_is_placeholder() keeps detecting it as unset.
    RAZORPAY_KEY_ID: str = Field(
        default="replace_me_razorpay_key_id", description="Razorpay API Key ID"
    )
    RAZORPAY_KEY_SECRET: str = Field(
        default="replace_me_razorpay_key_secret", description="Razorpay API Key Secret"
    )
    # This was previously missing from Settings entirely: app/api/v1/payments.py's
    # webhook handler read it via getattr(settings, "RAZORPAY_WEBHOOK_SECRET", ...),
    # which always fell through to the hardcoded default because pydantic-settings
    # only loads fields declared on the model - so no operator-configured env value
    # could ever reach it, regardless of what RAZORPAY_WEBHOOK_SECRET was set to.
    # (There was also a separate, unused PAYMENT_WEBHOOK_SECRET/
    # PAYMENT_WEBHOOK_TOLERANCE_SECONDS pair here from an earlier generic-webhook
    # design that no code ever read; removed rather than kept alongside this.)
    RAZORPAY_WEBHOOK_SECRET: str = Field(
        default="replace_me_razorpay_webhook_secret",
        description="Razorpay webhook signature verification secret",
    )

    # ─── WebSocket ────────────────────────────────────────────────────────
    WEBSOCKET_HEARTBEAT_INTERVAL: int = Field(
        default=30, description="WebSocket heartbeat interval in seconds"
    )
    WEBSOCKET_MAX_CONNECTIONS_PER_USER: int = Field(
        default=5,
        description="Maximum concurrent WebSocket connections per user",
    )

    # ─── WebSocket URL ────────────────────────────────────────────────────────
    WEBSOCKET_URL: str = Field(
        default="ws://localhost:8000/ws",
        description="WebSocket URL for clients (can be overridden via env var)",
    )

    # ─── Rate Limiting ────────────────────────────────────────────────────
    RATE_LIMIT_ENABLED: bool = Field(
        default=True, description="Enable rate limiting on API endpoints"
    )
    DEFAULT_RATE_LIMIT: str = Field(
        default="100/minute", description="Default rate limit (requests/time_window)"
    )
    AUTH_RATE_LIMIT: str = Field(
        default="10/minute", description="Rate limit specifically for authentication endpoints"
    )
    PREMIUM_RATE_LIMIT: str = Field(
        default="1000/minute", description="Rate limit for premium tier users"
    )

    MAX_TRACKED_SYMBOLS: int = Field(
        default=100, description="Maximum number of symbols to track in free tier (adjustable)."
    )
    BATCH_SIZE: int = Field(
        default=20, description="Number of symbols per batch request to yfinance."
    )


    @model_validator(mode="after")
    def validate_database_user(self) -> Settings:
        if self.ENVIRONMENT != "test":
            if "postgres:" in self.DATABASE_URL.lower():
                if self.ENVIRONMENT == "production":
                    raise ValueError("Cannot run as postgres superuser in production. Use nq_api role.")
        return self

    @model_validator(mode="after")
    def validate_production_keys(self) -> Settings:
        if self.ENVIRONMENT == "production":
            # UPSTOX_API_KEY/SECRET are intentionally not required here: this
            # app is documented as fully functional in paper-trading mode
            # with no broker keys at all (backend/.env.example, README.md).
            # upstox_service.py already raises its own clear error the
            # moment something actually tries to use the Upstox integration
            # without them configured - that's the right place for this
            # check, not a blanket production-startup crash that would take
            # down the entire app (including paper trading, which needs no
            # broker credentials) over an optional feature being unused.
            required_keys = {
                "DATABASE_URL": self.DATABASE_URL,
                "REDIS_URL": self.REDIS_URL,
            }
            for key, val in required_keys.items():
                val_lower = str(val).lower()
                if (
                    not val
                    or "changeme" in val_lower
                    or "your_" in val_lower
                    or "replace_me" in val_lower
                ):
                    raise ValueError(
                        f"Missing or insecure value for required production key: {key}"
                    )
        return self

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"



    @property
    def model_checkpoint_path(self) -> Path:
        """Get Path object for model checkpoint directory."""
        return Path(self.MODEL_CHECKPOINT_DIR)



# ─── Singleton Getter ──────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get singleton Settings instance.

    Settings are loaded from environment variables or backend/.env file.
    The root .env file is no longer used for the backend.
    """
    return Settings()
