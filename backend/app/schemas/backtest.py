"""Backtesting request/response schemas."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    """Request to run a backtest."""
    strategy_name: str = Field(
        ...,
        pattern="^(mean_reversion|momentum|volatility_breakout|ml_alpha|stat_arb)$",
    )
    symbols: List[str] = Field(..., min_length=1)
    start_date: date
    end_date: date
    benchmark: str = Field(default="^NSEI")
    initial_capital: float = Field(default=1000000.0, gt=0)
    commission_pct: float = Field(default=0.001, ge=0, description="Commission as fraction")
    slippage_pct: float = Field(default=0.0005, ge=0, description="Slippage as fraction")
    params: Optional[Dict[str, Any]] = Field(
        default=None, description="Strategy-specific parameters"
    )


class TradeRecord(BaseModel):
    """Single trade in the backtest trade log."""
    symbol: str
    entry_date: date
    exit_date: date
    direction: str
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    return_pct: float


class BacktestMetrics(BaseModel):
    """Backtest performance metrics."""
    total_return: float
    cagr: float
    sharpe_ratio: float
    sortino_ratio: Optional[float] = None
    max_drawdown: float
    calmar_ratio: Optional[float] = None
    win_rate: float
    profit_factor: Optional[float] = None
    total_trades: int
    avg_trade_duration_days: Optional[float] = None
    benchmark_return: Optional[float] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None


class BacktestResponse(BaseModel):
    """Complete backtest result response."""
    id: int
    strategy_name: str
    symbols: List[str]
    start_date: date
    end_date: date
    benchmark: str
    metrics: BacktestMetrics
    equity_curve: List[Dict[str, Any]]
    drawdown_curve: List[Dict[str, Any]]
    monthly_returns: List[Dict[str, Any]]
    trade_log: List[TradeRecord]
