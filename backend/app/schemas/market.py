"""Market data request/response schemas (Pydantic v2)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────━━
# Embedded Models (used in multiple responses)
# ─────────────────────────────────────────────────────────────━━

class RegimeData(BaseModel):
    """Regime state object."""
    state: str = Field(..., description="bull|bear|sideways|crisis")
    probs: list[float] = Field(..., description="[P(bull), P(bear), P(sideways), P(crisis)]")


class SignalData(BaseModel):
    """Signal object."""
    direction: str = Field(..., description="STRONG_BUY|BUY|NEUTRAL|SELL|STRONG_SELL")
    confidence: float = Field(..., ge=0.0, le=1.0)


# ─────────────────────────────────────────────────────────────━━
# Market Endpoints
# ─────────────────────────────────────────────────────────────━━

class QuoteResponse(BaseModel):
    """GET /market/quote/{symbol} response."""
    ticker: str
    name: str
    price: Decimal = Field(..., decimal_places=8)
    change: Decimal = Field(..., decimal_places=8)
    change_pct: Decimal = Field(..., decimal_places=4)
    volume: Decimal = Field(..., decimal_places=4)
    market_cap: Decimal | None = Field(None, decimal_places=2)
    pe_ratio: Decimal | None = Field(None, decimal_places=4)
    week_52_high: Decimal | None = Field(None, decimal_places=8)
    week_52_low: Decimal | None = Field(None, decimal_places=8)
    regime: RegimeData
    signal: SignalData
    timestamp: datetime
    data_freshness_seconds: int | None = None
    source: str = "realtime"


class OHLCVBar(BaseModel):
    """Single OHLCV candle."""
    time: int
    open: Decimal = Field(..., decimal_places=8)
    high: Decimal = Field(..., decimal_places=8)
    low: Decimal = Field(..., decimal_places=8)
    close: Decimal = Field(..., decimal_places=8)
    volume: Decimal = Field(..., decimal_places=4)


class HistoryResponse(BaseModel):
    """GET /market/history/{symbol} response."""
    symbol: str
    interval: str = Field(..., description="1m|5m|15m|1h|1d")
    bars: list[OHLCVBar]
    data_freshness_seconds: int | None = None
    source: str = "realtime"


class IndexData(BaseModel):
    """Single index in indices response."""
    name: str
    ticker: str
    value: Decimal = Field(..., decimal_places=8)
    change: Decimal = Field(..., decimal_places=8)
    change_pct: Decimal = Field(..., decimal_places=4)
    regime_state: str = Field(..., description="bull|bear|sideways|crisis")
    timestamp: datetime


class IndicesResponse(BaseModel):
    """GET /market/indices response."""
    indices: list[IndexData]


class MoverData(BaseModel):
    """Single asset in movers response."""
    ticker: str
    name: str
    exchange: str
    price: Decimal = Field(..., decimal_places=8)
    change_pct: Decimal = Field(..., decimal_places=4)
    volume: Decimal = Field(..., decimal_places=4)
    signal_direction: str
    signal_confidence: float
    rank: int


class MoversResponse(BaseModel):
    """GET /market/movers response."""
    assets: list[MoverData]
    exchange: str
    type: str = Field(..., description="gainers|losers|volume|momentum")
    generated_at: datetime


class SectorNode(BaseModel):
    """Sector treemap node."""
    ticker: str
    name: str
    value: Decimal = Field(..., decimal_places=4)
    metric_value: Decimal = Field(..., decimal_places=4)
    exchange: str


class HeatmapResponse(BaseModel):
    """GET /market/heatmap response."""
    exchange: str
    metric: str = Field(..., description="return_1d|return_5d|volume_surge")
    sectors: dict[str, list[SectorNode]]
    generated_at: datetime


class SearchResult(BaseModel):
    """Single search result."""
    ticker: str
    name: str
    exchange: str
    asset_type: str = Field(..., description="EQUITY|CRYPTO|INDEX|ETF|FOREX")


class SearchResponse(BaseModel):
    """GET /market/search response."""
    query: str
    results: list[SearchResult]
    total_matched: int


class EconomicEvent(BaseModel):
    """Single economic calendar event."""
    date: datetime
    event_name: str
    country: str
    importance: str = Field(..., description="low|medium|high")
    forecast: str | None = None
    previous: str | None = None


class EconomicCalendarResponse(BaseModel):
    """GET /market/economic-calendar response."""
    events: list[EconomicEvent]
    period_start: datetime
    period_end: datetime
    min_price: float | None = None
    max_price: float | None = None
    rsi_min: float | None = None
    rsi_max: float | None = None
    above_sma_200: bool | None = None
    volume_surge: bool | None = None
    ml_confidence_min: float | None = Field(None, ge=0, le=100)
    sort_by: str = Field(default="market_cap", description="Field to sort by")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class ScreenerResult(BaseModel):
    """Single screener result row."""
    symbol: str
    name: str
    asset_class: str
    exchange: str | None
    sector: str | None
    price: float
    change_percent: float
    volume: float
    market_cap: float | None
    rsi: float | None
    ml_signal: str | None
    ml_confidence: float | None


class ScreenerResponse(BaseModel):
    """Screener response with pagination."""
    results: list[ScreenerResult]
    total: int
    limit: int
    offset: int
