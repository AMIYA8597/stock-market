# Live data provider configuration

from pydantic import BaseSettings, Field

class LiveDataSettings(BaseSettings):
    """Configuration for live market data source selection and rate limiting."""
    # Choose between 'yfinance', 'alpha_vantage', 'coingecko', 'fred' etc.
    provider: str = Field(default="yfinance", description="Default live data provider")
    # Rate limit settings (requests per minute) for providers that need throttling
    yfinance_rate_limit: int = Field(default=5, description="Requests per minute for yfinance (if applicable)")
    alpha_vantage_rate_limit: int = Field(default=5, description="Requests per minute for Alpha Vantage")

    class Config:
        env_prefix = "LIVE_DATA_"  # e.g., LIVE_DATA_PROVIDER, LIVE_DATA_YFINANCE_RATE_LIMIT

# Export a singleton instance for easy import
settings = LiveDataSettings()
