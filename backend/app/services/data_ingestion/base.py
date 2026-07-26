"""Base abstractions and shared utilities for market data ingestion sources."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

import aiohttp
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

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


class HttpMarketDataProvider(MarketDataProvider, ABC):
    """Base class for providers backed by a plain HTTP endpoint.

    Provides a retrying request helper that maps HTTP failures onto provider
    errors, plus the health probe shared by all HTTP providers.
    """

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    health_symbol = "^NSEI"

    def __init__(self, timeout: int = 15):
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    @property
    def headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent}

    @retry(
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError, DataUnavailableError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _request(self, url: str, *, as_json: bool = False) -> Any:
        """Fetch ``url`` and return its body as parsed JSON or raw text."""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 429:
                    raise RateLimitExceededError(f"{self.name} rate limit exceeded.")
                if response.status == 404:
                    raise DataUnavailableError(f"{self.name} returned 404 for url: {url}")
                if response.status >= 400:
                    raise DataUnavailableError(f"{self.name} returned {response.status}")
                return await response.json() if as_json else await response.text()

    async def get_universe(self) -> list[dict]:
        """HTTP providers expose no instrument master by default."""
        return []

    async def health(self) -> dict:
        try:
            await self.get_quote(self.health_symbol)
            return {"status": "ok", "provider": self.name}
        except Exception as e:
            return {"status": "down", "provider": self.name, "error": str(e)}
