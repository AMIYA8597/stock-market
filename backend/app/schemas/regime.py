"""Regime detection and forecasting schemas (Pydantic v2)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class RegimeCurrentResponse(BaseModel):
    """GET /regime/current response."""

    state: str = Field(..., description="bull|bear|sideways|crisis")
    state_index: int = Field(..., ge=0, le=3)
    probs: list[Decimal] = Field(..., description="[P(bull), P(bear), P(sideways), P(crisis)]")
    transition_matrix: list[list[Decimal]] | None = Field(default=None, description="4x4 A matrix")
    cond_vol_1d: Decimal = Field(..., gt=0, description="conditional volatility 1-day")
    cond_vol_5d: Decimal = Field(..., gt=0)
    cond_vol_21d: Decimal = Field(..., gt=0)
    days_in_state: int = 1
    last_transition_date: datetime | None = None
    timestamp: datetime | None = None
    updated_at: datetime | None = None


class RegimeHistoryPoint(BaseModel):
    """Single point in regime history."""

    time: datetime
    state: str
    state_index: int
    probs: list[Decimal]
    cond_vol: Decimal = Field(..., gt=0)
    cond_vol_5d: Decimal | None = None
    cond_vol_21d: Decimal | None = None


class RegimeHistoryResponse(BaseModel):
    """GET /regime/history response."""

    period_days: int
    start_date: datetime
    end_date: datetime
    data: list[RegimeHistoryPoint]
    transitions: int = Field(..., description="number of regime changes in period")


class RegimeStatistics(BaseModel):
    """Per-state statistics."""

    state: str
    state_index: int
    avg_duration_days: Decimal = Field(...)
    frequency_pct: Decimal = Field(...)
    avg_daily_return: Decimal = Field(...)
    avg_volatility: Decimal = Field(..., gt=0)
    min_volatility: Decimal = Field(..., gt=0)
    max_volatility: Decimal = Field(..., gt=0)
    best_daily_return: Decimal = Field(...)
    worst_daily_return: Decimal = Field(...)


class RegimeStatisticsResponse(BaseModel):
    """GET /regime/statistics response."""

    period_days: int = Field(..., description="analysis period")
    statistics: list[RegimeStatistics] = Field(..., description="one per state")
    most_common_state: str
    mean_duration_all_states: Decimal = Field(...)
