"""Market data request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class QuoteResponse(BaseModel):
    """Real-time quote response."""
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: float
    high: float
    low: float
    open: float
    previous_close: float
    timestamp: datetime


class OHLCVBar(BaseModel):
    """Single OHLCV data point."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    adjusted_close: Optional[float] = None


class HistoryResponse(BaseModel):
    """Historical OHLCV data response."""
    symbol: str
    interval: str
    bars: List[OHLCVBar]
    count: int


class ScreenerFilter(BaseModel):
    """Screener query filter parameters."""
    asset_class: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    rsi_min: Optional[float] = None
    rsi_max: Optional[float] = None
    above_sma_200: Optional[bool] = None
    volume_surge: Optional[bool] = None
    ml_confidence_min: Optional[float] = Field(None, ge=0, le=100)
    sort_by: str = Field(default="market_cap", description="Field to sort by")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class ScreenerResult(BaseModel):
    """Single screener result row."""
    symbol: str
    name: str
    asset_class: str
    exchange: Optional[str]
    sector: Optional[str]
    price: float
    change_percent: float
    volume: float
    market_cap: Optional[float]
    rsi: Optional[float]
    ml_signal: Optional[str]
    ml_confidence: Optional[float]


class ScreenerResponse(BaseModel):
    """Screener response with pagination."""
    results: List[ScreenerResult]
    total: int
    limit: int
    offset: int
