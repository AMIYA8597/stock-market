"""Backtesting Engine Service API.

Provides comprehensive backtesting capabilities with multiple strategies,
performance analysis, and PDF report generation.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid

import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from .backtester.backtesting_engine import BacktestingEngine, create_strategy
from .reports.pdf_generator import BacktestReportGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
backtest_engine = BacktestingEngine()
report_generator = BacktestReportGenerator()


class BacktestRequest(BaseModel):
    """Request model for running backtests."""
    strategy_name: str = Field(..., description="Strategy to use")
    strategy_params: Optional[Dict[str, Any]] = Field(None, description="Strategy parameters")
    symbols: List[str] = Field(..., description="Symbols to trade")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    initial_capital: float = Field(1000000.0, description="Initial capital")
    commission_rate: float = Field(0.001, description="Commission rate")
    slippage_rate: float = Field(0.0005, description="Slippage rate")


class WalkForwardRequest(BaseModel):
    """Request model for walk-forward optimization."""
    strategy_name: str = Field(..., description="Strategy to optimize")
    param_ranges: Dict[str, List[Any]] = Field(..., description="Parameter ranges to test")
    symbols: List[str] = Field(..., description="Symbols to trade")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    n_windows: int = Field(5, description="Number of walk-forward windows")
    metric: str = Field("sharpe", description="Optimization metric")


class MonteCarloRequest(BaseModel):
    """Request model for Monte Carlo significance testing."""
    n_simulations: int = Field(1000, description="Number of simulations")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Backtesting Engine Service")
    yield
    logger.info("Shutting down Backtesting Engine Service")


app = FastAPI(
    title="NeuroQuant Backtesting Engine",
    description="Advanced backtesting service with multiple strategies and performance analysis",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "backtesting-engine"}


@app.post("/backtest")
async def run_backtest(request: BacktestRequest) -> Dict[str, Any]:
    """
    Run a backtest with specified strategy and parameters.

    Returns comprehensive backtest results including performance metrics,
    trade analysis, and risk statistics.
    """
    try:
        # Validate dates
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d")

        if start_date >= end_date:
            raise HTTPException(status_code=400, detail="Start date must be before end date")

        # Create strategy
        strategy = create_strategy(request.strategy_name, request.strategy_params)

        # Initialize backtest engine
        engine = BacktestingEngine(
            initial_capital=request.initial_capital,
            commission_rate=request.commission_rate,
            slippage_rate=request.slippage_rate
        )

        # Load sample data (in production, this would come from data pipeline)
        sample_data = generate_sample_data(request.symbols, start_date, end_date)
        engine.load_data(sample_data, start_date, end_date)
        engine.add_strategy(strategy)

        # Run backtest
        results = engine.run_backtest()

        # Convert pandas objects to JSON-serializable format
        serializable_results = serialize_results(results)

        return {
            "request_id": str(uuid.uuid4()),
            "strategy": request.strategy_name,
            "params": request.strategy_params,
            "date_range": {
                "start": request.start_date,
                "end": request.end_date
            },
            "symbols": request.symbols,
            "results": serializable_results
        }

    except Exception as e:
        logger.error(f"Backtest error: {e}")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@app.post("/backtest/walk-forward")
async def run_walk_forward_optimization(request: WalkForwardRequest) -> Dict[str, Any]:
    """
    Run walk-forward optimization for strategy parameters.

    Returns optimal parameters and out-of-sample performance.
    """
    try:
        # Validate dates
        start_date = datetime.strptime(request.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(request.end_date, "%Y-%m-%d")

        # Create sample data
        sample_data = generate_sample_data(request.symbols, start_date, end_date)

        # Initialize engine
        engine = BacktestingEngine()
        engine.load_data(sample_data, start_date, end_date)

        # Run walk-forward optimization
        results = engine.walk_forward_optimization(
            data=sample_data,
            strategy_class=create_strategy(request.strategy_name).__class__,
            param_ranges=request.param_ranges,
            n_windows=request.n_windows,
            metric=request.metric
        )

        return {
            "request_id": str(uuid.uuid4()),
            "strategy": request.strategy_name,
            "optimization_metric": request.metric,
            "results": results
        }

    except Exception as e:
        logger.error(f"Walk-forward optimization error: {e}")
        raise HTTPException(status_code=500, detail=f"Walk-forward optimization failed: {str(e)}")


@app.post("/backtest/monte-carlo")
async def run_monte_carlo_test(request: MonteCarloRequest) -> Dict[str, Any]:
    """
    Run Monte Carlo significance testing on the last backtest results.

    Returns p-value and significance assessment.
    """
    try:
        if not backtest_engine.results:
            raise HTTPException(status_code=400, detail="No backtest results available. Run a backtest first.")

        results = backtest_engine.monte_carlo_significance_test(request.n_simulations)

        return {
            "request_id": str(uuid.uuid4()),
            "n_simulations": request.n_simulations,
            "results": results
        }

    except Exception as e:
        logger.error(f"Monte Carlo test error: {e}")
        raise HTTPException(status_code=500, detail=f"Monte Carlo test failed: {str(e)}")


@app.post("/report/generate")
async def generate_pdf_report(
    strategy_name: str = "Strategy",
    author: str = "NeuroQuant"
) -> Dict[str, Any]:
    """
    Generate PDF report from the last backtest results.

    Returns PDF content as base64-encoded string.
    """
    try:
        if not backtest_engine.results:
            raise HTTPException(status_code=400, detail="No backtest results available. Run a backtest first.")

        # Generate PDF
        pdf_bytes = report_generator.generate_report(
            results=backtest_engine.results,
            strategy_name=strategy_name,
            author=author
        )

        # Convert to base64
        import base64
        pdf_b64 = base64.b64encode(pdf_bytes).decode('utf-8')

        return {
            "request_id": str(uuid.uuid4()),
            "strategy_name": strategy_name,
            "author": author,
            "pdf_content": pdf_b64,
            "content_type": "application/pdf"
        }

    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@app.get("/strategies")
async def get_available_strategies() -> Dict[str, List[str]]:
    """Get list of available trading strategies."""
    return {
        "strategies": [
            "kalman_pairs",
            "adaptive_momentum",
            "ml_alpha",
            "stat_arb",
            "vol_regime",
            "rl_agent"
        ],
        "descriptions": {
            "kalman_pairs": "Kalman Filter Pairs Trading",
            "adaptive_momentum": "Adaptive Momentum with Regime Filter",
            "ml_alpha": "ML Alpha Strategy using model predictions",
            "stat_arb": "Statistical Arbitrage - Index Rebalancing",
            "vol_regime": "Volatility Regime Strategy",
            "rl_agent": "Deep RL Agent Strategy"
        }
    }


@app.get("/strategies/{strategy_name}/params")
async def get_strategy_params(strategy_name: str) -> Dict[str, Any]:
    """Get default parameters for a strategy."""
    try:
        strategy = create_strategy(strategy_name)
        return {
            "strategy": strategy_name,
            "parameters": strategy.get_params()
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


def generate_sample_data(symbols: List[str], start_date: datetime, end_date: datetime) -> Dict[str, pd.DataFrame]:
    """Generate sample OHLCV data for testing."""
    np.random.seed(42)

    data = {}
    current_date = start_date

    # Generate 500 trading days of data
    dates = pd.date_range(start_date, end_date, freq='B')  # Business days

    for symbol in symbols:
        # Generate random walk prices
        n_days = len(dates)
        returns = np.random.normal(0.0005, 0.02, n_days)  # Mean return 0.05%, vol 2%
        prices = 1000 * np.exp(np.cumsum(returns))  # Start at 1000

        # Create OHLCV data
        high_mult = 1 + np.random.uniform(0, 0.02, n_days)
        low_mult = 1 - np.random.uniform(0, 0.02, n_days)
        volume_base = np.random.uniform(100000, 1000000, n_days)

        ohlcv_data = []
        for i, price in enumerate(prices):
            open_price = price * (1 + np.random.normal(0, 0.005))
            high_price = price * high_mult[i]
            low_price = price * low_mult[i]
            close_price = price
            volume = int(volume_base[i])

            ohlcv_data.append({
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume
            })

        df = pd.DataFrame(ohlcv_data, index=dates)
        data[symbol] = df

    return data


def serialize_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """Convert pandas objects to JSON-serializable format."""
    serializable = {}

    for key, value in results.items():
        if isinstance(value, pd.Series):
            serializable[key] = {
                'index': value.index.strftime('%Y-%m-%d').tolist() if hasattr(value.index, 'strftime') else value.index.tolist(),
                'values': value.tolist()
            }
        elif isinstance(value, pd.DataFrame):
            serializable[key] = {
                'index': value.index.strftime('%Y-%m-%d').tolist() if hasattr(value.index, 'strftime') else value.index.tolist(),
                'columns': value.columns.tolist(),
                'data': value.values.tolist()
            }
        elif isinstance(value, dict):
            serializable[key] = serialize_results(value)
        else:
            serializable[key] = value

    return serializable


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8005,
        reload=True,
        log_level="info"
    )