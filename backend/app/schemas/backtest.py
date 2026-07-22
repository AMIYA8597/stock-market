"""Backtesting schemas (Pydantic v2)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────━━
# Backtest Request
# ─────────────────────────────────────────────────────────────━━

class WalkForwardConfig(BaseModel):
    """Walk-forward cross-validation configuration."""
    enabled: bool = True
    n_splits: int = Field(default=8, ge=2, le=20)
    purge_days: int = Field(default=5, ge=0)
    embargo_days: int = Field(default=5, ge=0)


class MonteCarloConfig(BaseModel):
    """Monte Carlo simulation configuration."""
    enabled: bool = True
    n_simulations: int = Field(default=10000, ge=100, le=100000)


class BacktestRequest(BaseModel):
    """POST /backtest/run request body."""
    strategy_name: str = Field(..., description="ensemble|tft_only|ma_crossover|rsi_mrv|custom")
    strategy_params: dict = Field(default_factory=dict, description="custom strategy params")
    universe: list[str] = Field(..., min_length=1, max_length=500, description="list of symbols")
    date_from: date
    date_to: date
    initial_capital: Decimal = Field(..., gt=0)
    walk_forward: WalkForwardConfig | None = None
    monte_carlo: MonteCarloConfig | None = None


# ─────────────────────────────────────────────────────────────━━
# Backtest Status
# ─────────────────────────────────────────────────────────────━━

class BacktestStatusResponse(BaseModel):
    """GET /backtest/status/{job_id} response."""
    job_id: str
    status: str = Field(..., description="PENDING|RUNNING|DONE|FAILED")
    progress_pct: int = Field(..., ge=0, le=100)
    current_date: date | None = None
    equity_value: Decimal | None = None
    estimated_remaining_seconds: int | None = None
    error_message: str | None = None
    result_preview: dict | None = None


# ─────────────────────────────────────────────────────────────━━
# Backtest Results
# ─────────────────────────────────────────────────────────────━━

class BacktestMetrics(BaseModel):
    """Core backtest performance metrics."""
    total_return: Decimal = Field(...)
    cagr: Decimal = Field(...)
    sharpe: Decimal = Field(...)
    sharpe_ratio: Decimal = Field(...)
    sortino_ratio: Decimal = Field(...)
    calmar_ratio: Decimal = Field(...)
    omega_ratio: Decimal = Field(...)
    max_drawdown: Decimal = Field(...)
    max_drawdown_duration_days: int
    win_rate: Decimal = Field(..., ge=0, le=1)
    profit_factor: Decimal = Field(...)
    avg_win: Decimal = Field(...)
    avg_loss: Decimal = Field(...)
    payoff_ratio: Decimal = Field(...)
    num_trades: int
    gross_profit: Decimal = Field(...)
    gross_loss: Decimal = Field(...)
    tail_ratio: Decimal = Field(...)
    serenity_ratio: Decimal = Field(...)
    deflated_sharpe: Decimal = Field(...)


class EquityCurvePoint(BaseModel):
    """Single point in equity curve."""
    date: date
    portfolio_value: Decimal = Field(...)
    benchmark_value: Decimal | None = Field(None)


class DrawdownPoint(BaseModel):
    """Single drawdown data point."""
    date: date
    drawdown_pct: Decimal = Field(...)


class TradeLogEntry(BaseModel):
    """Single trade in trade log."""
    date: date
    symbol: str
    direction: str = Field(..., description="BUY|SELL")
    quantity: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    pnl: Decimal = Field(...)
    cum_pnl: Decimal = Field(...)
    commission: Decimal = Field(...)


class WalkForwardMetrics(BaseModel):
    """Walk-forward analysis results."""
    fold_sharpes: list[Decimal] = Field(..., description="Sharpe per fold")
    mean_sharpe: Decimal = Field(...)
    std_sharpe: Decimal = Field(...)
    t_statistic: Decimal = Field(...)
    p_value: Decimal = Field(..., ge=0, le=1)


class MonteCarloResults(BaseModel):
    """Monte Carlo simulation results."""
    percentiles: dict[str, Decimal] = Field(..., description="p5, p25, p50, p75, p95")
    prob_of_ruin_10pct: Decimal = Field(..., ge=0, le=1)
    prob_of_ruin_25pct: Decimal = Field(..., ge=0, le=1)
    fan_paths_sample: list[list[Decimal]] = Field(..., description="100 sample paths")


class StatisticalTests(BaseModel):
    """Statistical significance tests."""
    dm_test_statistic: Decimal = Field(...)
    dm_test_p_value: Decimal = Field(..., ge=0, le=1)
    dm_test_vs_benchmark: str = Field(default="ARIMA")
    sharpe_se: Decimal = Field(..., description="Sharpe standard error")
    min_backtest_length_days: int
    multiple_testing_correction: str = "Bonferroni"


class BacktestResultsResponse(BaseModel):
    """GET /backtest/results/{job_id} complete response."""
    job_id: str
    strategy_name: str
    universe: list[str]
    date_from: date
    date_to: date
    initial_capital: Decimal = Field(...)

    metrics: BacktestMetrics
    equity_curve: list[EquityCurvePoint]
    drawdown_series: list[DrawdownPoint]
    trade_log: list[TradeLogEntry]

    walk_forward: WalkForwardMetrics | None = None
    monte_carlo: MonteCarloResults | None = None
    statistical_tests: StatisticalTests | None = None

    status: str = "DONE"
    completed_at: datetime
    excluded_tickers: list[dict] | None = None

class BacktestRunResponse(BaseModel):
    """POST /backtest/run response."""
    job_id: str
    status: str = "PENDING"
    estimated_seconds: int
    universe_size: int
    period_days: int
    strategy_name: str = "custom"
