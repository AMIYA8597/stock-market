"""
Pydantic schemas for backtesting endpoints.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class BacktestRequest(BaseModel):
    """Backtest request schema."""
    strategy_name: str = Field(..., description="Trading strategy name")
    symbols: List[str] = Field(..., min_items=1, max_items=50, description="List of symbols to test")
    start_date: datetime
    end_date: datetime
    initial_capital: int = Field(default=10000000, ge=100000, le=100000000, description="Initial capital in rupees")
    parameters: Optional[Dict[str, float]] = Field(default=None, description="Strategy parameters")

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, v):
        """Validate symbol formats."""
        import re
        for symbol in v:
            if not re.match(r'^[A-Z0-9.-]{1,20}$', symbol):
                raise ValueError(f"Invalid symbol format: {symbol}")
        return [s.upper() for s in v]

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v, info):
        """Validate date range."""
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class BacktestResultResponse(BaseModel):
    """Backtest result response."""
    backtest_id: str
    strategy_name: str
    symbols: List[str]
    start_date: datetime
    end_date: datetime
    initial_capital: int
    final_capital: int
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_duration: int  # Days
    max_consecutive_losses: int
    calmar_ratio: float
    omega_ratio: float
    recovery_factor: float


class TradeLogResponse(BaseModel):
    """Individual trade log response."""
    trade_id: str
    symbol: str
    side: str  # BUY or SELL
    quantity: int
    entry_price: float
    exit_price: Optional[float]
    entry_date: datetime
    exit_date: Optional[datetime]
    pnl: Optional[float]
    pnl_percent: Optional[float]
    duration_days: Optional[int]
    entry_reason: str
    exit_reason: Optional[str]


class BacktestDetailedResponse(BacktestResultResponse):
    """Detailed backtest response with trade logs."""
    trades: List[TradeLogResponse]
    equity_curve: List[Dict[str, float]]  # Date-value pairs
    drawdown_curve: List[Dict[str, float]]
    monthly_returns: List[Dict[str, float]]
    risk_metrics: Dict[str, float]


class StrategyInfoResponse(BaseModel):
    """Strategy information response."""
    name: str
    description: str
    parameters: Dict[str, Dict[str, float]]  # Parameter name -> {min, max, default}
    required_data: List[str]  # Required data fields
    universe: str  # Asset universe description


class MonteCarloRequest(BaseModel):
    """Monte Carlo simulation request."""
    backtest_id: str
    num_simulations: int = Field(default=1000, ge=100, le=10000)
    confidence_level: float = Field(default=0.95, ge=0.8, le=0.99)


class MonteCarloResponse(BaseModel):
    """Monte Carlo simulation response."""
    backtest_id: str
    num_simulations: int
    confidence_level: float
    expected_return: float
    return_std: float
    var_95: float
    cvar_95: float
    probability_loss: float
    max_drawdown_95: float
    simulation_results: List[float]


class WalkForwardRequest(BaseModel):
    """Walk-forward optimization request."""
    strategy_name: str
    symbols: List[str]
    start_date: datetime
    end_date: datetime
    window_size_months: int = Field(default=12, ge=6, le=60)
    step_size_months: int = Field(default=1, ge=1, le=12)
    parameters: Optional[Dict[str, List[float]]] = None


class WalkForwardResponse(BaseModel):
    """Walk-forward optimization response."""
    strategy_name: str
    total_windows: int
    in_sample_periods: List[Dict[str, datetime]]
    out_sample_periods: List[Dict[str, datetime]]
    window_results: List[Dict[str, float]]
    overall_performance: Dict[str, float]
    parameter_stability: Dict[str, float]


class BacktestingResponse(BaseModel):
    """Generic backtesting response."""
    success: bool
    message: str
    data: Optional[dict] = None