"""
Pydantic schemas for market data endpoints.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class OHLCVBase(BaseModel):
    """Base OHLCV data schema."""
    symbol: str = Field(..., min_length=1, max_length=20, description="Stock symbol")
    exchange: str = Field(..., min_length=1, max_length=10, description="Exchange code")
    open: float = Field(..., gt=0, description="Opening price")
    high: float = Field(..., gt=0, description="Highest price")
    low: float = Field(..., gt=0, description="Lowest price")
    close: float = Field(..., gt=0, description="Closing price")
    volume: int = Field(..., ge=0, description="Trading volume")


class OHLCVResponse(OHLCVBase):
    """OHLCV response schema."""
    time: datetime

    class Config:
        from_attributes = True


class QuoteResponse(BaseModel):
    """Real-time quote response."""
    symbol: str
    exchange: str
    price: float
    change: float
    change_percent: float
    volume: int
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None


class HistoricalDataRequest(BaseModel):
    """Historical data request schema."""
    symbol: str = Field(..., min_length=1, max_length=20)
    exchange: str = Field(..., min_length=1, max_length=10)
    start_date: datetime
    end_date: datetime
    interval: str = Field(default="1d", description="Time interval (1m, 5m, 1h, 1d, 1w, 1M)")

    @field_validator("interval")
    @classmethod
    def validate_interval(cls, v):
        """Validate time interval."""
        valid_intervals = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
        if v not in valid_intervals:
            raise ValueError(f"Invalid interval. Must be one of: {', '.join(valid_intervals)}")
        return v

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v, info):
        """Validate date range."""
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class HistoricalDataResponse(BaseModel):
    """Historical data response schema."""
    symbol: str
    exchange: str
    interval: str
    data: List[OHLCVResponse]


class MarketIndexResponse(BaseModel):
    """Market index response."""
    symbol: str
    name: str
    value: float
    change: float
    change_percent: float
    timestamp: datetime


class MarketOverviewResponse(BaseModel):
    """Market overview response."""
    indices: List[MarketIndexResponse]
    top_gainers: List[QuoteResponse]
    top_losers: List[QuoteResponse]
    most_active: List[QuoteResponse]
    timestamp: datetime


class EconomicIndicatorResponse(BaseModel):
    """Economic indicator response."""
    indicator: str
    name: str
    value: float
    unit: str
    change: Optional[float] = None
    change_percent: Optional[float] = None
    timestamp: datetime
    source: str


class MarketDataResponse(BaseModel):
    """Generic market data response."""
    success: bool
    message: str
    data: Optional[dict] = None