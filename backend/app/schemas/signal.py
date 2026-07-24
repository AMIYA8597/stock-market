"""Signal and model prediction schemas (Pydantic v2)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

# ─────────────────────────────────────────────────────────────━━
# TFT Model Output
# ─────────────────────────────────────────────────────────────━━


class SignalResponse(BaseModel):
    """GET /signals/{symbol} complete response for classical technical signals."""

    model_config = ConfigDict(protected_namespaces=())

    symbol: str
    timestamp: datetime
    direction: str = Field(..., description="STRONG_BUY|BUY|NEUTRAL|SELL|STRONG_SELL")
    confidence: float = Field(..., ge=0.0, le=1.0)
    score: float = Field(..., ge=-1.0, le=1.0)
    breakdown: dict[str, float] = Field(..., description="per-indicator contribution list")
    patterns: list[str] = Field(default_factory=list, description="detected patterns")
    stop_loss: float = 0.0
    take_profit: float = 0.0
    position_size_pct: float = Field(0.0, description="position-size from account-risk %")

class BulkSignalResponse(BaseModel):
    """GET /signals/bulk response."""

    symbols: list[str]
    signals: list[SignalResponse]
    generated_at: datetime
    total_symbols: int
    processed_symbols: int

class HistoricalSignal(BaseModel):
    """Single point in signal history."""

    time: datetime
    signal: Decimal = Field(..., ge=-1.0, le=1.0)
    confidence: Decimal = Field(..., ge=0.0, le=1.0)
    direction: str
    actual_return: Decimal | None = Field(None)

class SignalHistoryResponse(BaseModel):
    """GET /signals/history/{symbol} response."""

    symbol: str
    model: str = Field(..., description="ensemble|tft|hmm_garch|gnn|lstm_attn|xgboost")
    period_days: int
    data: list[HistoricalSignal]
    accuracy_metrics: dict | None = None
