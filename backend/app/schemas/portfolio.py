"""Portfolio management schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PortfolioCreate(BaseModel):
    """Create a new portfolio."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    initial_capital: float = Field(default=100000.0, gt=0)


class HoldingAdd(BaseModel):
    """Add or update a holding in a portfolio."""
    symbol: str
    quantity: float = Field(..., gt=0)
    avg_cost: float = Field(..., gt=0)


class HoldingResponse(BaseModel):
    """Portfolio holding with current market data."""
    symbol: str
    quantity: float
    avg_cost: float
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    weight: Optional[float] = None
    added_at: datetime

    model_config = {"from_attributes": True}


class PortfolioResponse(BaseModel):
    """Portfolio summary response."""
    id: int
    name: str
    description: Optional[str]
    initial_capital: float
    holdings: List[HoldingResponse]
    total_value: Optional[float] = None
    total_pnl: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RiskMetrics(BaseModel):
    """Portfolio risk metrics."""
    var_95: float = Field(..., description="Value at Risk at 95% confidence")
    var_99: float = Field(..., description="Value at Risk at 99% confidence")
    cvar_95: float = Field(..., description="Conditional VaR (Expected Shortfall) 95%")
    max_drawdown: float
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    beta: Optional[float] = None
    alpha: Optional[float] = None
    correlation_matrix: Optional[Dict[str, Dict[str, float]]] = None


class OptimizeRequest(BaseModel):
    """Portfolio optimization request."""
    portfolio_id: int
    method: str = Field(
        default="max_sharpe",
        pattern="^(max_sharpe|min_volatility|efficient_risk|hrp)$",
    )
    risk_free_rate: float = Field(default=0.05)
    target_return: Optional[float] = None


class OptimizeResponse(BaseModel):
    """Portfolio optimization result."""
    method: str
    weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
