"""Base abstractions and shared utilities for market data ingestion sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

Interval = Literal["1m", "5m", "15m", "1h", "1d"]

@dataclass(slots=True, frozen=True)
class OHLCVBar:
    """Normalized OHLCV data point."""
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    adjusted_close: float | None
    interval: Interval

@dataclass(slots=True, frozen=True)
class Quote:
    """Normalized Quote data point."""
    symbol: str
    price: float
    change: float
    change_pct: float
    volume: float
    timestamp: datetime

class ProviderError(Exception):
    """Base class for provider errors."""
    pass

class DataUnavailableError(ProviderError):
    """Raised when data is unavailable from the source."""
    pass

class RateLimitExceededError(ProviderError):
    """Raised when the provider rate limit is exceeded."""
    pass

class MarketDataProvider(ABC):
    """Abstract interface for all market data sources."""
    name: str

    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote:
        """Fetch real-time or delayed quote."""
        pass

    @abstractmethod
    async def get_ohlcv(
        self, symbol: str, interval: Interval, start: datetime, end: datetime
    ) -> list[OHLCVBar]:
        """Fetch OHLCV bars."""
        pass

    @abstractmethod
    async def get_universe(self) -> list[dict]:
        """Fetch universe of instruments."""
        pass

    @abstractmethod
    async def health(self) -> dict:
        """Return health status of the provider."""
        pass
