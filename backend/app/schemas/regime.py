"""Regime detection and forecasting schemas (Pydantic v2)."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class RegimeCurrentResponse(BaseModel):
    """GET /regime/current response."""
    state: str = Field(..., description="bull|bear|sideways|crisis")
    state_index: int = Field(..., ge=0, le=3)
    probs: list[Decimal] = Field(..., description="[P(bull), P(bear), P(sideways), P(crisis)]")
    transition_matrix: list[list[Decimal]] = Field(..., description="4x4 A matrix")
    cond_vol_1d: Decimal = Field(..., gt=0, decimal_places=6, description="conditional volatility 1-day")
    cond_vol_5d: Decimal = Field(..., gt=0, decimal_places=6)
    cond_vol_21d: Decimal = Field(..., gt=0, decimal_places=6)
    days_in_state: int
    last_transition_date: datetime
    timestamp: datetime


class RegimeHistoryPoint(BaseModel):
    """Single point in regime history."""
    time: datetime
    state: str
    state_index: int
    probs: list[Decimal]
    cond_vol: Decimal = Field(..., gt=0, decimal_places=6)
    cond_vol_5d: Optional[Decimal] = None
    cond_vol_21d: Optional[Decimal] = None


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
    avg_duration_days: Decimal = Field(..., decimal_places=2)
    frequency_pct: Decimal = Field(..., decimal_places=2)
    avg_daily_return: Decimal = Field(..., decimal_places=6)
    avg_volatility: Decimal = Field(..., gt=0, decimal_places=6)
    min_volatility: Decimal = Field(..., gt=0, decimal_places=6)
    max_volatility: Decimal = Field(..., gt=0, decimal_places=6)
    best_daily_return: Decimal = Field(..., decimal_places=6)
    worst_daily_return: Decimal = Field(..., decimal_places=6)


class RegimeStatisticsResponse(BaseModel):
    """GET /regime/statistics response."""
    period_days: int = Field(..., description="analysis period")
    statistics: list[RegimeStatistics] = Field(..., description="one per state")
    most_common_state: str
    mean_duration_all_states: Decimal = Field(..., decimal_places=2)
