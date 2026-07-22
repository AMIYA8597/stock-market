"""Portfolio management schemas (Pydantic v2)."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────━━
# Portfolio Holdings
# ─────────────────────────────────────────────────────────────━━

class HoldingData(BaseModel):
    """Single holding in portfolio."""
    symbol: str
    quantity: Decimal = Field(..., gt=0)
    avg_price: Decimal = Field(..., gt=0)
    current_price: Decimal = Field(..., gt=0)
    unrealized_pnl: Decimal = Field(...)
    unrealized_pnl_pct: Decimal = Field(...)
    in_position_days: int


class HoldingsResponse(BaseModel):
    """GET /portfolio/holdings response."""
    holdings: list[HoldingData]
    total_invested: Decimal = Field(...)
    total_current_value: Decimal = Field(...)
    total_unrealized_pnl: Decimal = Field(...)
    total_unrealized_pnl_pct: Decimal = Field(...)
    cash_balance: Decimal = Field(...)
    portfolio_value: Decimal = Field(...)
    timestamp: datetime


# ─────────────────────────────────────────────────────────────━━
# Transactions
# ─────────────────────────────────────────────────────────────━━

class TransactionRequest(BaseModel):
    """POST /portfolio/transaction request body."""
    symbol: str
    type: str = Field(..., description="BUY|SELL")
    quantity: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    brokerage: Decimal | None = Field(default=0, ge=0)
    stt: Decimal | None = Field(default=0, ge=0)


class TransactionResponse(BaseModel):
    """POST /portfolio/transaction response."""
    transaction_id: str
    symbol: str
    type: str
    quantity: Decimal = Field(...)
    price: Decimal = Field(...)
    net_amount: Decimal = Field(...)
    timestamp: datetime
    portfolio_updated: bool


# ─────────────────────────────────────────────────────────────━━
# Portfolio Performance
# ─────────────────────────────────────────────────────────────━━

class PerformancePoint(BaseModel):
    """Single point in performance time-series."""
    date: datetime
    portfolio_value: Decimal = Field(...)
    benchmark_value: Decimal = Field(...)
    daily_return: Decimal = Field(...)
    benchmark_return: Decimal = Field(...)


class PerformanceResponse(BaseModel):
    """GET /portfolio/performance response."""
    series: list[PerformancePoint]
    start_date: datetime
    end_date: datetime
    total_return: Decimal = Field(...)
    benchmark_return: Decimal = Field(...)
    excess_return: Decimal = Field(...)


# ─────────────────────────────────────────────────────────────━━
# Risk Metrics
# ─────────────────────────────────────────────────────────────━━

class RiskMetricsResponse(BaseModel):
    """GET /portfolio/risk-metrics response."""
    sharpe_ratio: Decimal = Field(...)
    sortino_ratio: Decimal = Field(...)
    beta: Decimal = Field(...)
    alpha: Decimal = Field(...)
    max_drawdown: Decimal = Field(...)
    var_95: Decimal = Field(..., description="Value at Risk 95%")
    cvar_95: Decimal = Field(..., description="Conditional VaR 95% (Expected Shortfall)")
    treynor_ratio: Decimal = Field(...)
    information_ratio: Decimal = Field(...)
    calmar_ratio: Decimal = Field(...)
    portfolio_volatility: Decimal = Field(..., gt=0)
    benchmark_volatility: Decimal = Field(..., gt=0)


# ─────────────────────────────────────────────────────────────━━
# Portfolio Optimization
# ─────────────────────────────────────────────────────────────━━

class OptimizationConstraints(BaseModel):
    """Portfolio optimization constraints."""
    max_weight: Decimal = Field(default=Decimal("0.20"), ge=0, le=1)
    min_weight: Decimal = Field(default=Decimal("0.0"), ge=0, le=1)
    sector_limits: dict[str, Decimal] | None = None
    max_turnover: Decimal | None = Field(None, ge=0)
    leverage_limit: Decimal = Field(default=Decimal("1.0"), ge=1)


class OptimizationRequest(BaseModel):
    """POST /portfolio/optimize request body."""
    universe: list[str] = Field(..., min_length=2, max_length=500)
    method: str = Field(..., description="hrp|black_litterman|cvar|mean_variance")
    constraints: OptimizationConstraints | None = None
    use_ml_views: bool = True


class OptimizedWeight(BaseModel):
    """Single optimized weight."""
    symbol: str
    weight: Decimal = Field(..., ge=0, le=1)


class EfficientFrontierPoint(BaseModel):
    """Single point on efficient frontier."""
    expected_return: Decimal = Field(...)
    expected_volatility: Decimal = Field(...)
    sharpe_ratio: Decimal = Field(...)
    weights: dict[str, Decimal]


class HRPDendrogramNode(BaseModel):
    """Single node in HRP dendrogram."""
    symbols: list[str]
    left: Optional['HRPDendrogramNode'] = None
    right: Optional['HRPDendrogramNode'] = None
    distance: Decimal = Field(...)


HRPDendrogramNode.model_rebuild()


class OptimizationResponse(BaseModel):
    """POST /portfolio/optimize response."""
    method: str
    weights: list[OptimizedWeight]
    expected_return: Decimal = Field(...)
    expected_volatility: Decimal = Field(...)
    sharpe_ratio: Decimal = Field(...)
    efficient_frontier: list[EfficientFrontierPoint] | None = None
    hrp_dendrogram: dict | None = None
    bl_posterior_returns: dict[str, Decimal] | None = None
    excluded_tickers: list[dict] | None = None
    timestamp: datetime
