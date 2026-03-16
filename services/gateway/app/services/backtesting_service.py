"""
Backtesting service implementation.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis_client
from app.schemas.backtesting import (
    BacktestRequest,
    BacktestResponse,
    MonteCarloRequest,
    MonteCarloResponse,
    WalkForwardRequest,
    WalkForwardResponse,
)


class BacktestingService:
    """Service for handling backtesting operations."""

    def __init__(self):
        self.redis = get_redis_client()
        self.backtesting_engine_url = "http://backtesting-engine:8005"  # Internal service URL
        self.cache_ttl = 1800  # 30 minutes

    async def run_backtest(
        self,
        request: BacktestRequest,
        user_id: str,
        db: AsyncSession
    ) -> BacktestResponse:
        """
        Run a backtest for a trading strategy.
        """
        cache_key = f"backtest:{request.symbol}:{request.strategy}:{request.start_date}:{request.end_date}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return BacktestResponse(**json.loads(cached_data))

        try:
            # Call backtesting engine
            async with httpx.AsyncClient(timeout=120.0) as client:  # 2 minute timeout
                response = await client.post(
                    f"{self.backtesting_engine_url}/backtest",
                    json={
                        "symbol": request.symbol,
                        "strategy": request.strategy,
                        "start_date": request.start_date,
                        "end_date": request.end_date,
                        "initial_capital": request.initial_capital,
                        "commission": request.commission,
                        "slippage": request.slippage,
                        "parameters": request.parameters or {}
                    }
                )
                response.raise_for_status()
                backtest_result = response.json()

            backtest_response = BacktestResponse(
                backtest_id=backtest_result["backtest_id"],
                symbol=request.symbol,
                strategy=request.strategy,
                start_date=request.start_date,
                end_date=request.end_date,
                initial_capital=request.initial_capital,
                final_capital=backtest_result["final_capital"],
                total_return=backtest_result["total_return"],
                annualized_return=backtest_result["annualized_return"],
                volatility=backtest_result["volatility"],
                sharpe_ratio=backtest_result["sharpe_ratio"],
                max_drawdown=backtest_result["max_drawdown"],
                win_rate=backtest_result["win_rate"],
                total_trades=backtest_result["total_trades"],
                profitable_trades=backtest_result["profitable_trades"],
                commission_paid=backtest_result["commission_paid"],
                trades=backtest_result["trades"],
                equity_curve=backtest_result["equity_curve"],
                drawdown_curve=backtest_result["drawdown_curve"],
                monthly_returns=backtest_result["monthly_returns"],
                risk_metrics=backtest_result["risk_metrics"],
                execution_time_seconds=backtest_result["execution_time_seconds"],
                timestamp=datetime.utcnow().isoformat()
            )

            # Cache the result
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(backtest_response.dict()))

            return backtest_response

        except httpx.RequestError as e:
            raise Exception(f"Failed to connect to backtesting engine: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"Backtesting engine error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to run backtest: {str(e)}")

    async def run_monte_carlo(
        self,
        request: MonteCarloRequest,
        user_id: str,
        db: AsyncSession
    ) -> MonteCarloResponse:
        """
        Run Monte Carlo simulation for portfolio.
        """
        cache_key = f"monte_carlo:{request.symbol}:{request.simulations}:{request.time_horizon}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return MonteCarloResponse(**json.loads(cached_data))

        try:
            # Call backtesting engine for Monte Carlo
            async with httpx.AsyncClient(timeout=180.0) as client:  # 3 minute timeout
                response = await client.post(
                    f"{self.backtesting_engine_url}/monte-carlo",
                    json={
                        "symbol": request.symbol,
                        "simulations": request.simulations,
                        "time_horizon": request.time_horizon,
                        "initial_investment": request.initial_investment,
                        "expected_return": request.expected_return,
                        "volatility": request.volatility,
                        "confidence_level": request.confidence_level
                    }
                )
                response.raise_for_status()
                mc_result = response.json()

            mc_response = MonteCarloResponse(
                symbol=request.symbol,
                simulations=request.simulations,
                time_horizon=request.time_horizon,
                initial_investment=request.initial_investment,
                expected_final_values=mc_result["expected_final_values"],
                value_at_risk_95=mc_result["value_at_risk_95"],
                expected_shortfall_95=mc_result["expected_shortfall_95"],
                probability_of_loss=mc_result["probability_of_loss"],
                best_case=mc_result["best_case"],
                worst_case=mc_result["worst_case"],
                median_outcome=mc_result["median_outcome"],
                mean_return=mc_result["mean_return"],
                volatility_of_returns=mc_result["volatility_of_returns"],
                confidence_intervals=mc_result["confidence_intervals"],
                simulation_paths=mc_result["simulation_paths"][:100],  # Limit to first 100 paths
                timestamp=datetime.utcnow().isoformat()
            )

            # Cache the result
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(mc_response.dict()))

            return mc_response

        except Exception as e:
            raise Exception(f"Failed to run Monte Carlo simulation: {str(e)}")

    async def run_walk_forward(
        self,
        request: WalkForwardRequest,
        user_id: str,
        db: AsyncSession
    ) -> WalkForwardResponse:
        """
        Run walk-forward optimization.
        """
        cache_key = f"walk_forward:{request.symbol}:{request.strategy}:{request.window_size}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return WalkForwardResponse(**json.loads(cached_data))

        try:
            # Call backtesting engine for walk-forward
            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minute timeout
                response = await client.post(
                    f"{self.backtesting_engine_url}/walk-forward",
                    json={
                        "symbol": request.symbol,
                        "strategy": request.strategy,
                        "start_date": request.start_date,
                        "end_date": request.end_date,
                        "window_size": request.window_size,
                        "step_size": request.step_size,
                        "parameters": request.parameters or {}
                    }
                )
                response.raise_for_status()
                wf_result = response.json()

            wf_response = WalkForwardResponse(
                symbol=request.symbol,
                strategy=request.strategy,
                start_date=request.start_date,
                end_date=request.end_date,
                window_size=request.window_size,
                step_size=request.step_size,
                out_of_sample_periods=wf_result["out_of_sample_periods"],
                average_oos_return=wf_result["average_oos_return"],
                oos_sharpe_ratio=wf_result["oos_sharpe_ratio"],
                oos_max_drawdown=wf_result["oos_max_drawdown"],
                parameter_stability=wf_result["parameter_stability"],
                overfitting_probability=wf_result["overfitting_probability"],
                robustness_score=wf_result["robustness_score"],
                walk_forward_windows=wf_result["walk_forward_windows"],
                optimal_parameters=wf_result["optimal_parameters"],
                performance_summary=wf_result["performance_summary"],
                timestamp=datetime.utcnow().isoformat()
            )

            # Cache the result
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(wf_response.dict()))

            return wf_response

        except Exception as e:
            raise Exception(f"Failed to run walk-forward optimization: {str(e)}")

    async def get_backtest_strategies(self, db: AsyncSession) -> List[Dict]:
        """
        Get list of available backtesting strategies.
        """
        cache_key = "backtest_strategies"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return json.loads(cached_data)

        try:
            # Call backtesting engine for strategies
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.backtesting_engine_url}/strategies")
                response.raise_for_status()
                strategies = response.json()

            # Cache for 1 hour
            await self.redis.setex(cache_key, 3600, json.dumps(strategies))

            return strategies

        except Exception as e:
            raise Exception(f"Failed to get backtest strategies: {str(e)}")

    async def get_strategy_parameters(
        self,
        strategy: str,
        db: AsyncSession
    ) -> Dict:
        """
        Get parameters for a specific strategy.
        """
        cache_key = f"strategy_params:{strategy}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return json.loads(cached_data)

        try:
            # Call backtesting engine for strategy parameters
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.backtesting_engine_url}/strategies/{strategy}/parameters")
                response.raise_for_status()
                params = response.json()

            # Cache for 1 hour
            await self.redis.setex(cache_key, 3600, json.dumps(params))

            return params

        except Exception as e:
            raise Exception(f"Failed to get strategy parameters: {str(e)}")

    async def compare_strategies(
        self,
        symbol: str,
        strategies: List[str],
        start_date: str,
        end_date: str,
        initial_capital: float,
        db: AsyncSession
    ) -> Dict:
        """
        Compare multiple strategies on the same data.
        """
        cache_key = f"strategy_comparison:{symbol}:{','.join(strategies)}:{start_date}:{end_date}"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return json.loads(cached_data)

        try:
            # Call backtesting engine for strategy comparison
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    f"{self.backtesting_engine_url}/compare",
                    json={
                        "symbol": symbol,
                        "strategies": strategies,
                        "start_date": start_date,
                        "end_date": end_date,
                        "initial_capital": initial_capital
                    }
                )
                response.raise_for_status()
                comparison = response.json()

            # Cache the result
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(comparison))

            return comparison

        except Exception as e:
            raise Exception(f"Failed to compare strategies: {str(e)}")

    async def get_backtest_history(
        self,
        user_id: str,
        limit: int = 50,
        db: AsyncSession = None
    ) -> List[Dict]:
        """
        Get user's backtest history.
        """
        # TODO: Implement backtest history storage and retrieval
        return [
            {
                "backtest_id": "bt-123",
                "symbol": "RELIANCE",
                "strategy": "SMA_Crossover",
                "total_return": 15.5,
                "sharpe_ratio": 1.45,
                "max_drawdown": -8.5,
                "timestamp": "2024-01-15T10:30:00Z"
            }
        ]