"""Configuration for Data Pipeline Service."""

from __future__ import annotations

from pydantic import Field
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
    DEFAULT_FETCH_PERIOD: str = "5d"
    DEFAULT_FETCH_INTERVAL: str = "1m"

    # Market schedule
    MARKET_TIMEZONE: str = "Asia/Kolkata"
    NSE_MARKET_OPEN_HOUR: int = 9
    NSE_MARKET_OPEN_MINUTE: int = 15
    NSE_MARKET_CLOSE_HOUR: int = 15
    NSE_MARKET_CLOSE_MINUTE: int = 30
    FETCH_INTERVAL_MINUTES: int = 15
    OFF_HOURS_PUBLISH_INTERVAL_MINUTES: int = 1

    # Symbol universes
    NSE_SYMBOLS: list[str] = Field(
        default_factory=lambda: [
            "RELIANCE.NS",
            "TCS.NS",
            "HDFCBANK.NS",
            "ICICIBANK.NS",
            "INFY.NS",
            "HINDUNILVR.NS",
            "ITC.NS",
            "KOTAKBANK.NS",
            "LT.NS",
            "AXISBANK.NS",
        ]
    )
    CRYPTO_SYMBOLS: list[str] = Field(
        default_factory=lambda: [
            "BTC-USD",
            "ETH-USD",
            "BNB-USD",
            "SOL-USD",
            "ADA-USD",
            "XRP-USD",
            "DOGE-USD",
            "AVAX-USD",
            "LTC-USD",
            "MATIC-USD",
        ]
    )


settings = Settings()