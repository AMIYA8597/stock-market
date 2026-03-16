"""
Pydantic schemas for portfolio endpoints.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class PortfolioBase(BaseModel):
    """Base portfolio schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Portfolio name")
    description: Optional[str] = Field(None, max_length=1000, description="Portfolio description")


class PortfolioCreate(PortfolioBase):
    """Portfolio creation schema."""
    pass


class PortfolioUpdate(BaseModel):
    """Portfolio update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class PortfolioResponse(PortfolioBase):
    """Portfolio response schema."""
    id: str
    user_id: str
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HoldingBase(BaseModel):
    """Base holding schema."""
    symbol: str = Field(..., min_length=1, max_length=20, description="Stock symbol")
    exchange: str = Field(..., min_length=1, max_length=10, description="Exchange code")
    quantity: int = Field(..., gt=0, description="Number of shares")
    average_cost: int = Field(..., gt=0, description="Average cost in paisa (1/100 of rupee)")

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        """Validate stock symbol format."""
        import re
        if not re.match(r'^[A-Z0-9.-]{1,20}$', v):
            raise ValueError("Invalid symbol format")
        return v.upper()


class HoldingCreate(HoldingBase):
    """Holding creation schema."""
    pass


class HoldingUpdate(BaseModel):
    """Holding update schema."""
    quantity: Optional[int] = Field(None, gt=0)
    average_cost: Optional[int] = Field(None, gt=0)


class HoldingResponse(HoldingBase):
    """Holding response schema."""
    id: str
    portfolio_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PortfolioHoldingResponse(HoldingResponse):
    """Portfolio holding with current price info."""
    current_price: Optional[int] = None  # In paisa
    market_value: Optional[int] = None   # In paisa
    unrealized_pnl: Optional[int] = None # In paisa
    unrealized_pnl_percent: Optional[float] = None


class PortfolioSummaryResponse(BaseModel):
    """Portfolio summary response."""
    portfolio: PortfolioResponse
    holdings: List[PortfolioHoldingResponse]
    total_value: int  # In paisa
    total_cost: int   # In paisa
    total_pnl: int    # In paisa
    total_pnl_percent: float
    day_pnl: int      # In paisa
    day_pnl_percent: float


class PortfolioPerformanceResponse(BaseModel):
    """Portfolio performance response."""
    portfolio_id: str
    start_date: datetime
    end_date: datetime
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    best_day: float
    worst_day: float
    equity_curve: List[Dict[str, float]]  # Date-value pairs


class RebalanceRequest(BaseModel):
    """Portfolio rebalancing request."""
    target_weights: Dict[str, float] = Field(..., description="Target weights by symbol")

    @field_validator("target_weights")
    @classmethod
    def validate_weights(cls, v):
        """Validate that weights sum to approximately 1.0."""
        total = sum(v.values())
        if not 0.99 <= total <= 1.01:
            raise ValueError("Target weights must sum to 1.0")
        return v


class RebalanceResponse(BaseModel):
    """Portfolio rebalancing response."""
    current_weights: Dict[str, float]
    target_weights: Dict[str, float]
    trades_required: List[Dict[str, float]]  # Buy/sell orders
    estimated_cost: int  # In paisa
    expected_impact: Dict[str, float]


class OptimizationRequest(BaseModel):
    """Portfolio optimization request."""
    method: str = Field(..., description="Optimization method")
    constraints: Optional[Dict[str, float]] = None
    risk_free_rate: float = Field(default=0.05, ge=0, le=0.2)

    @field_validator("method")
    @classmethod
    def validate_method(cls, v):
        """Validate optimization method."""
        valid_methods = [
            "mean_variance", "min_variance", "max_sharpe",
            "hierarchical_risk_parity", "black_litterman"
        ]
        if v not in valid_methods:
            raise ValueError(f"Invalid method. Must be one of: {', '.join(valid_methods)}")
        return v


class OptimizationResponse(BaseModel):
    """Portfolio optimization response."""
    optimal_weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    optimization_metrics: Dict[str, float]


class PortfolioResponse(BaseModel):
    """Generic portfolio response."""
    success: bool
    message: str
    data: Optional[dict] = None