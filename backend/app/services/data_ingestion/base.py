"""Base abstractions and shared utilities for market data ingestion sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

Interval = Literal["1m", "5m", "15m", "1h", "1d"]


@dataclass(slots=True, frozen=True)
class OHLCVBar:
    """Normalized OHLCV data point used by all ingestion adapters.

    Args:
        time: Timestamp in UTC.
        open: Open price.
        high: High price.
        low: Low price.
        close: Close price.
        volume: Traded volume.
        adjusted_close: Adjusted close when provided by source.
        interval: Time interval label.
    """

    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    adjusted_close: float | None
    interval: Interval


class DataSourceError(RuntimeError):
    """Raised when a source adapter cannot fetch or normalize data."""


class MarketDataSource(ABC):
    """Abstract interface for asynchronous OHLCV sources."""

    name: str

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        interval: Interval,
        start: datetime,
        end: datetime,
    ) -> list[OHLCVBar]:
        """Fetch OHLCV bars for a symbol within [start, end]."""
