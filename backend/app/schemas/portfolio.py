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
    quantity: Decimal = Field(..., gt=0, decimal_places=8)
    avg_price: Decimal = Field(..., gt=0, decimal_places=8)
    current_price: Decimal = Field(..., gt=0, decimal_places=8)
    unrealized_pnl: Decimal = Field(..., decimal_places=2)
    unrealized_pnl_pct: Decimal = Field(..., decimal_places=4)
    in_position_days: int


class HoldingsResponse(BaseModel):
    """GET /portfolio/holdings response."""
    holdings: list[HoldingData]
    total_invested: Decimal = Field(..., decimal_places=2)
    total_current_value: Decimal = Field(..., decimal_places=2)
    total_unrealized_pnl: Decimal = Field(..., decimal_places=2)
    total_unrealized_pnl_pct: Decimal = Field(..., decimal_places=4)
    cash_balance: Decimal = Field(..., decimal_places=2)
    portfolio_value: Decimal = Field(..., decimal_places=2)
    timestamp: datetime


# ─────────────────────────────────────────────────────────────━━
# Transactions
# ─────────────────────────────────────────────────────────────━━

class TransactionRequest(BaseModel):
    """POST /portfolio/transaction request body."""
    symbol: str
    type: str = Field(..., description="BUY|SELL")
    quantity: Decimal = Field(..., gt=0, decimal_places=8)
    price: Decimal = Field(..., gt=0, decimal_places=8)
    brokerage: Optional[Decimal] = Field(default=0, ge=0, decimal_places=4)
    stt: Optional[Decimal] = Field(default=0, ge=0, decimal_places=4)


class TransactionResponse(BaseModel):
    """POST /portfolio/transaction response."""
    transaction_id: str
    symbol: str
    type: str
    quantity: Decimal = Field(..., decimal_places=8)
    price: Decimal = Field(..., decimal_places=8)
    net_amount: Decimal = Field(..., decimal_places=2)
    timestamp: datetime
    portfolio_updated: bool


# ─────────────────────────────────────────────────────────────━━
# Portfolio Performance
# ─────────────────────────────────────────────────────────────━━

class PerformancePoint(BaseModel):
    """Single point in performance time-series."""
    date: datetime
    portfolio_value: Decimal = Field(..., decimal_places=2)
    benchmark_value: Decimal = Field(..., decimal_places=2)
    daily_return: Decimal = Field(..., decimal_places=6)
    benchmark_return: Decimal = Field(..., decimal_places=6)


class PerformanceResponse(BaseModel):
    """GET /portfolio/performance response."""
    series: list[PerformancePoint]
    start_date: datetime
    end_date: datetime
    total_return: Decimal = Field(..., decimal_places=4)
    benchmark_return: Decimal = Field(..., decimal_places=4)
    excess_return: Decimal = Field(..., decimal_places=4)


# ─────────────────────────────────────────────────────────────━━
# Risk Metrics
# ─────────────────────────────────────────────────────────────━━

class RiskMetricsResponse(BaseModel):
    """GET /portfolio/risk-metrics response."""
    sharpe_ratio: Decimal = Field(..., decimal_places=4)
    sortino_ratio: Decimal = Field(..., decimal_places=4)
    beta: Decimal = Field(..., decimal_places=4)
    alpha: Decimal = Field(..., decimal_places=4)
    max_drawdown: Decimal = Field(..., decimal_places=4)
    var_95: Decimal = Field(..., decimal_places=4, description="Value at Risk 95%")
    cvar_95: Decimal = Field(..., decimal_places=4, description="Conditional VaR 95% (Expected Shortfall)")
    treynor_ratio: Decimal = Field(..., decimal_places=4)
    information_ratio: Decimal = Field(..., decimal_places=4)
    calmar_ratio: Decimal = Field(..., decimal_places=4)
    portfolio_volatility: Decimal = Field(..., gt=0, decimal_places=4)
    benchmark_volatility: Decimal = Field(..., gt=0, decimal_places=4)


# ─────────────────────────────────────────────────────────────━━
# Portfolio Optimization
# ─────────────────────────────────────────────────────────────━━

class OptimizationConstraints(BaseModel):
    """Portfolio optimization constraints."""
    max_weight: Decimal = Field(default=Decimal("0.20"), ge=0, le=1, decimal_places=4)
    min_weight: Decimal = Field(default=Decimal("0.0"), ge=0, le=1, decimal_places=4)
    sector_limits: Optional[dict[str, Decimal]] = None
    max_turnover: Optional[Decimal] = Field(None, ge=0, decimal_places=4)
    leverage_limit: Decimal = Field(default=Decimal("1.0"), ge=1, decimal_places=2)


class OptimizationRequest(BaseModel):
    """POST /portfolio/optimize request body."""
    universe: list[str] = Field(..., min_length=2, max_length=500)
    method: str = Field(..., description="hrp|black_litterman|cvar|mean_variance")
    constraints: Optional[OptimizationConstraints] = None
    use_ml_views: bool = True


class OptimizedWeight(BaseModel):
    """Single optimized weight."""
    symbol: str
    weight: Decimal = Field(..., ge=0, le=1, decimal_places=4)


class EfficientFrontierPoint(BaseModel):
    """Single point on efficient frontier."""
    expected_return: Decimal = Field(..., decimal_places=4)
    expected_volatility: Decimal = Field(..., decimal_places=4)
    sharpe_ratio: Decimal = Field(..., decimal_places=4)
    weights: dict[str, Decimal]


class HRPDendrogramNode(BaseModel):
    """Single node in HRP dendrogram."""
    symbols: list[str]
    left: Optional['HRPDendrogramNode'] = None
    right: Optional['HRPDendrogramNode'] = None
    distance: Decimal = Field(..., decimal_places=6)


HRPDendrogramNode.model_rebuild()


class OptimizationResponse(BaseModel):
    """POST /portfolio/optimize response."""
    method: str
    weights: list[OptimizedWeight]
    expected_return: Decimal = Field(..., decimal_places=4)
    expected_volatility: Decimal = Field(..., decimal_places=4)
    sharpe_ratio: Decimal = Field(..., decimal_places=4)
    efficient_frontier: Optional[list[EfficientFrontierPoint]] = None
    hrp_dendrogram: Optional[dict] = None
    bl_posterior_returns: Optional[dict[str, Decimal]] = None
    timestamp: datetime
