"""Screener and alerts schemas (Pydantic v2)."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, model_validator

# ─────────────────────────────────────────────────────────────━━
# Screener
# ─────────────────────────────────────────────────────────────━━

class ScreenerFilterConfig(BaseModel):
    """Screener filter configuration."""
    asset_class: str | None = None
    exchange: list[str] | str | None = None
    market_cap_min: Decimal | None = None
    market_cap_max: Decimal | None = None
    pe_ratio_max: Decimal | None = None
    rsi_min: Decimal | None = None
    rsi_max: Decimal | None = None
    momentum_21d_min: Decimal | None = None
    volume_ratio_min: Decimal | None = None
    signal_direction: list[str] | str | None = None
    regime_compatible: bool = False
    
    # Extra fields sent by frontend
    min_market_cap: Decimal | None = None
    max_market_cap: Decimal | None = None
    above_sma_200: bool | None = None
    volume_surge: bool | None = None
    ml_confidence_min: Decimal | None = None

    @model_validator(mode="before")
    @classmethod
    def map_aliases_and_types(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # map min_market_cap -> market_cap_min
            if "min_market_cap" in data and data["min_market_cap"] is not None:
                data["market_cap_min"] = data["min_market_cap"]
            if "max_market_cap" in data and data["max_market_cap"] is not None:
                data["market_cap_max"] = data["max_market_cap"]
            # convert exchange from str to list
            if "exchange" in data:
                ex = data["exchange"]
                if isinstance(ex, str):
                    data["exchange"] = [ex]
            # convert signal_direction from str to list
            if "signal_direction" in data:
                sd = data["signal_direction"]
                if isinstance(sd, str):
                    data["signal_direction"] = [sd]
        return data


class ScreenerRunRequest(BaseModel):
    """POST /screener/run request body."""
    exchange: list[str] = Field(..., description="NSE, NYSE, NASDAQ, CRYPTO, etc")
    filters: ScreenerFilterConfig
    sort_by: str = Field(default="sharpe_21d")
    limit: int = Field(default=50, ge=1, le=500)


class ScreenerResult(BaseModel):
    """Single screener result."""
    ticker: str
    name: str
    exchange: str
    asset_type: str
    price: Decimal = Field(..., decimal_places=8)
    change_pct: Decimal = Field(..., decimal_places=4)
    pe_ratio: Decimal | None = None
    rsi: Decimal | None = None
    signal_direction: str
    signal_confidence: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    regime_state: str
    momentum_21d: Decimal = Field(..., decimal_places=4)
    volume_ratio: Decimal = Field(..., decimal_places=4)


class ScreenerRunResponse(BaseModel):
    """POST /screener/run response."""
    results: list[ScreenerResult]
    total_matched: int
    filters_applied: dict
    generated_at: datetime


class ScreenerPreset(BaseModel):
    """Single screener preset."""
    name: str
    description: str
    filters_json: dict
    created_at: datetime


class ScreenerPresetsResponse(BaseModel):
    """GET /screener/presets response."""
    presets: list[ScreenerPreset]


# ─────────────────────────────────────────────────────────────━━
# Alerts
# ─────────────────────────────────────────────────────────────━━

class AlertCreateRequest(BaseModel):
    """POST /alerts request body."""
    symbol: str | None = None
    alert_type: str = Field(..., description="PRICE_ABOVE|PRICE_BELOW|RSI_OB|MACD_CROSS|SIGNAL_CHANGE|REGIME_CHANGE")
    threshold: Decimal | None = None
    name: str = Field(..., min_length=1, max_length=100)
    enabled: bool = True


class AlertData(BaseModel):
    """Alert object."""
    id: str
    symbol: str | None = None
    alert_type: str
    threshold: Decimal | None = None
    name: str
    enabled: bool
    is_triggered: bool
    triggered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AlertListResponse(BaseModel):
    """GET /alerts response."""
    alerts: list[AlertData]
    total_count: int


class AlertUpdateRequest(BaseModel):
    """PATCH /alerts/{id} request body."""
    name: str | None = None
    threshold: Decimal | None = None
    enabled: bool | None = None


class AlertUpdateResponse(BaseModel):
    """PATCH /alerts/{id} response."""
    alert: AlertData


class AlertDeleteResponse(BaseModel):
    """DELETE /alerts/{id} response."""
    id: str
    deleted_at: datetime
