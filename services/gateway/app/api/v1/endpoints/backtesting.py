"""
Backtesting engine endpoints.
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user_with_permissions
from app.core.database import get_db
from app.schemas.backtesting import (
    BacktestDetailedResponse,
    BacktestRequest,
    BacktestResultResponse,
    MonteCarloRequest,
    MonteCarloResponse,
    StrategyInfoResponse,
    WalkForwardRequest,
    WalkForwardResponse,
)
from app.services.backtesting_service import BacktestingService

router = APIRouter()
backtesting_service = BacktestingService()


@router.post("/run", response_model=BacktestResultResponse)
async def run_backtest(
    backtest_data: BacktestRequest,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Run a backtest with specified strategy and parameters.
    """
    # Convert to service format
    service_request = {
        "symbol": backtest_data.symbols[0] if backtest_data.symbols else "NIFTY50",  # Use first symbol or default
        "strategy": backtest_data.strategy_name,
        "start_date": backtest_data.start_date.isoformat(),
        "end_date": backtest_data.end_date.isoformat(),
        "initial_capital": backtest_data.initial_capital,
        "commission": 0.0005,  # Default commission
        "slippage": 0.001,  # Default slippage
        "parameters": backtest_data.parameters or {}
    }

    result = await backtesting_service.run_backtest(service_request, current_user["user_id"], db)

    return BacktestResultResponse(
        backtest_id=result.backtest_id,
        strategy_name=result.strategy,
        symbols=backtest_data.symbols,
        start_date=result.start_date,
        end_date=result.end_date,
        initial_capital=result.initial_capital,
        final_capital=result.final_capital,
        total_return=result.total_return,
        annualized_return=result.annualized_return,
        volatility=result.volatility,
        sharpe_ratio=result.sharpe_ratio,
        sortino_ratio=result.risk_metrics.get("sortino_ratio", 0.0),
        max_drawdown=result.max_drawdown,
        win_rate=result.win_rate,
        profit_factor=result.risk_metrics.get("profit_factor", 0.0),
        total_trades=result.total_trades,
        avg_trade_duration=result.risk_metrics.get("avg_trade_duration", 0),
        max_consecutive_losses=result.risk_metrics.get("max_consecutive_losses", 0),
        calmar_ratio=result.risk_metrics.get("calmar_ratio", 0.0),
        omega_ratio=result.risk_metrics.get("omega_ratio", 0.0)
    )


@router.get("/result/{backtest_id}", response_model=BacktestDetailedResponse)
async def get_backtest_result(
    backtest_id: str,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed backtest results including trade log.
    """
    # For now, return mock data - in production this would fetch from database
    return BacktestDetailedResponse(
        backtest_id=backtest_id,
        strategy_name="Adaptive Momentum",
        symbols=["RELIANCE", "TCS", "HDFC"],
        start_date=datetime(2020, 1, 1),
        end_date=datetime(2023, 12, 31),
        initial_capital=10000000,
        final_capital=12500000,
        total_return=0.25,
        annualized_return=0.08,
        volatility=0.15,
        sharpe_ratio=1.23,
        sortino_ratio=1.45,
        max_drawdown=0.12,
        win_rate=0.62,
        profit_factor=1.75,
        total_trades=150,
        avg_trade_duration=25,
        max_consecutive_losses=5,
        calmar_ratio=0.67,
        omega_ratio=1.35,
        trades=[],  # TODO: Get from service
        equity_curve=[],  # TODO: Get from service
        drawdown_curve=[],  # TODO: Get from service
        monthly_returns=[],  # TODO: Get from service
        risk_metrics={"var_95": 0.08, "cvar_95": 0.12, "beta": 0.85}
    )


@router.post("/monte-carlo", response_model=MonteCarloResponse)
async def run_monte_carlo(
    mc_data: MonteCarloRequest,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Run Monte Carlo simulation on backtest results.
    """
    # Convert to service format
    service_request = {
        "symbol": "NIFTY50",  # Default symbol
        "simulations": mc_data.num_simulations,
        "time_horizon": 252,  # Trading days in a year
        "initial_investment": 10000000,  # Default amount
        "expected_return": 0.08,  # 8% expected return
        "volatility": 0.15,  # 15% volatility
        "confidence_level": mc_data.confidence_level
    }

    result = await backtesting_service.run_monte_carlo(service_request, current_user["user_id"], db)

    return MonteCarloResponse(
        backtest_id=mc_data.backtest_id,
        num_simulations=result.simulations,
        confidence_level=mc_data.confidence_level,
        expected_return=result.mean_return,
        return_std=result.volatility_of_returns,
        var_95=result.value_at_risk_95,
        cvar_95=result.expected_shortfall_95,
        probability_loss=result.probability_of_loss,
        max_drawdown_95=result.risk_metrics.get("max_drawdown_95", 0.0),
        simulation_results=result.expected_final_values[:5]  # First 5 results
    )


@router.post("/walk-forward", response_model=WalkForwardResponse)
async def run_walk_forward(
    wf_data: WalkForwardRequest,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Run walk-forward optimization.
    """
    # Convert to service format
    service_request = {
        "symbol": "NIFTY50",  # Default symbol
        "strategy": wf_data.strategy_name,
        "start_date": "2020-01-01",
        "end_date": "2023-12-31",
        "window_size": 252,  # 1 year
        "step_size": 63,  # 3 months
        "parameters": wf_data.parameters or {}
    }

    result = await backtesting_service.run_walk_forward(service_request, current_user["user_id"], db)

    return WalkForwardResponse(
        strategy_name=result.strategy,
        total_windows=result.out_of_sample_periods,
        in_sample_periods=[],  # TODO: Map from result
        out_sample_periods=[],  # TODO: Map from result
        window_results=[],  # TODO: Map from result
        overall_performance={
            "sharpe_ratio": result.oos_sharpe_ratio,
            "max_drawdown": result.oos_max_drawdown,
            "win_rate": 0.65  # TODO: Calculate
        },
        parameter_stability=result.parameter_stability
    )


@router.get("/strategies", response_model=List[StrategyInfoResponse])
async def list_strategies(
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    List available trading strategies.
    """
    strategies = await backtesting_service.get_backtest_strategies(db)

    return [
        StrategyInfoResponse(
            name=strategy["name"],
            description=strategy.get("description", ""),
            parameters=strategy.get("parameters", {}),
            required_data=strategy.get("required_data", ["close"]),
            universe=strategy.get("universe", "NSE500")
        )
        for strategy in strategies
    ]