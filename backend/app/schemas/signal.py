"""Signal and model prediction schemas (Pydantic v2)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

# ─────────────────────────────────────────────────────────────━━
# TFT Model Output
# ─────────────────────────────────────────────────────────────━━

class TFTSignal(BaseModel):
    """TFT model prediction."""
    p10_return: Decimal = Field(..., decimal_places=6, description="10th percentile")
    p50_return: Decimal = Field(..., decimal_places=6, description="median forecast")
    p90_return: Decimal = Field(..., decimal_places=6, description="90th percentile")
    raw_signal: Decimal = Field(..., ge=-1.0, le=1.0, decimal_places=4)
    horizon_days: int = Field(..., description="1|5|21")


class HMMGARCHSignal(BaseModel):
    """HMM-GARCH regime and volatility forecast."""
    regime_signal: Decimal = Field(..., ge=-1.0, le=1.0, decimal_places=4)
    vol_forecast_1d: Decimal = Field(..., gt=0, decimal_places=6)
    vol_forecast_5d: Decimal = Field(..., gt=0, decimal_places=6)
    vol_forecast_21d: Decimal = Field(..., gt=0, decimal_places=6)


class GNNSignal(BaseModel):
    """GNN spillover risk and correlation."""
    spillover_risk: Decimal = Field(..., ge=0.0, le=1.0, decimal_places=4)
    embedding_norm: Decimal = Field(..., gt=0, decimal_places=6)
    top_correlated_assets: list[dict] = Field(..., description="[{ticker, correlation}]")


class LSTMAttentionSignal(BaseModel):
    """LSTM with attention weights."""
    raw_signal: Decimal = Field(..., ge=-1.0, le=1.0, decimal_places=4)
    attention_peaks: list[dict] = Field(..., description="[{date, weight}]")


class XGBoostSignal(BaseModel):
    """XGBoost classification signal."""
    raw_signal: Decimal = Field(..., ge=-1.0, le=1.0, decimal_places=4)
    top_features: list[dict] = Field(..., description="[{name, shap_value}]")


class EnsembleSignal(BaseModel):
    """Final ensemble signal."""
    signal: Decimal = Field(..., ge=-1.0, le=1.0, decimal_places=4)
    confidence: Decimal = Field(..., ge=0.0, le=1.0, decimal_places=4)
    direction: str = Field(..., description="STRONG_BUY|BUY|NEUTRAL|SELL|STRONG_SELL")
    kelly_fraction: Decimal = Field(..., ge=0.0, le=0.25, decimal_places=4)


class SignalResponse(BaseModel):
    """GET /signals/{symbol} complete response."""
    model_config = ConfigDict(protected_namespaces=())

    symbol: str
    timestamp: datetime
    ensemble: EnsembleSignal
    models: dict = Field(
        ...,
        description="tft, hmm_garch, gnn, lstm_attn, xgboost model outputs"
    )
    model_weights: dict[str, Decimal] = Field(..., description="per-model weight")
    regime: dict = Field(..., description="state, probs, transition_matrix")
    is_computed: bool = False
    message: str = ""
    target_price_5d: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    prob_buy: float = 0.5
    prob_sell: float = 0.5
    max_loss_pct: float = 0.0


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
    signal: Decimal = Field(..., ge=-1.0, le=1.0, decimal_places=4)
    confidence: Decimal = Field(..., ge=0.0, le=1.0, decimal_places=4)
    direction: str
    actual_return: Decimal | None = Field(None, decimal_places=6)


class SignalHistoryResponse(BaseModel):
    """GET /signals/history/{symbol} response."""
    symbol: str
    model: str = Field(..., description="ensemble|tft|hmm_garch|gnn|lstm_attn|xgboost")
    period_days: int
    data: list[HistoricalSignal]
    accuracy_metrics: dict | None = None
