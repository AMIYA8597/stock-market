"""Risk Engine Service API.

Provides portfolio risk calculations: VaR, CVaR, Monte Carlo simulation,
portfolio optimization, and stress testing.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import logging
from typing import Dict, List, Any, Optional
import uuid

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from .risk_engine import RiskEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global risk engine instance
risk_engine = RiskEngine()


class PortfolioRequest(BaseModel):
    """Request model for portfolio risk calculations."""
    returns_data: Dict[str, List[float]] = Field(..., description="Asset returns data")
    weights: Optional[List[float]] = Field(None, description="Portfolio weights")
    confidence_level: float = Field(0.95, description="Confidence level for VaR")
    position_size: float = Field(1.0, description="Portfolio position size")


class VaRRequest(PortfolioRequest):
    """Request model for VaR calculations."""
    method: str = Field("historical", description="VaR method: historical, parametric, monte_carlo")


class MonteCarloRequest(PortfolioRequest):
    """Request model for Monte Carlo simulation."""
    n_simulations: int = Field(1000, description="Number of simulation paths")
    n_days: int = Field(252, description="Number of days to simulate")


class OptimizationRequest(BaseModel):
    """Request model for portfolio optimization."""
    returns_data: Dict[str, List[float]] = Field(..., description="Asset returns data")
    method: str = Field("mean_variance", description="Optimization method")
    target_return: Optional[float] = Field(None, description="Target portfolio return")


class StressTestRequest(BaseModel):
    """Request model for stress testing."""
    returns_data: Dict[str, List[float]] = Field(..., description="Asset returns data")
    weights: List[float] = Field(..., description="Portfolio weights")
    scenarios: Dict[str, Dict[str, float]] = Field(..., description="Stress scenarios")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Risk Engine Service")
    yield
    logger.info("Shutting down Risk Engine Service")


app = FastAPI(
    title="NeuroQuant Risk Engine",
    description="Portfolio risk calculation service",
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
    return {"status": "healthy", "service": "risk-engine"}


@app.post("/var")
async def calculate_var(request: VaRRequest) -> Dict[str, Any]:
    """
    Calculate Value at Risk using specified method.

    Returns VaR for the portfolio at given confidence level.
    """
    try:
        # Convert returns data to DataFrame
        returns_df = pd.DataFrame(request.returns_data)

        # Calculate VaR
        result = risk_engine.calculate_var(
            returns=returns_df,
            method=request.method,
            confidence=request.confidence_level,
            position=request.position_size
        )

        return {
            "request_id": str(uuid.uuid4()),
            "method": request.method,
            "confidence_level": request.confidence_level,
            "position_size": request.position_size,
            "var_result": result
        }

    except Exception as e:
        logger.error(f"VaR calculation error: {e}")
        raise HTTPException(status_code=500, detail=f"VaR calculation failed: {str(e)}")


@app.post("/cvar")
async def calculate_cvar(request: PortfolioRequest) -> Dict[str, Any]:
    """
    Calculate Conditional Value at Risk (Expected Shortfall).

    Returns CVaR for the portfolio at given confidence level.
    """
    try:
        returns_df = pd.DataFrame(request.returns_data)

        result = risk_engine.calculate_cvar(
            returns=returns_df,
            confidence=request.confidence_level,
            position=request.position_size
        )

        return {
            "request_id": str(uuid.uuid4()),
            "confidence_level": request.confidence_level,
            "position_size": request.position_size,
            "cvar_result": result
        }

    except Exception as e:
        logger.error(f"CVaR calculation error: {e}")
        raise HTTPException(status_code=500, detail=f"CVaR calculation failed: {str(e)}")


@app.post("/monte-carlo")
async def run_monte_carlo(request: MonteCarloRequest) -> Dict[str, Any]:
    """
    Run Monte Carlo portfolio simulation.

    Returns simulation statistics and percentile analysis.
    """
    try:
        returns_df = pd.DataFrame(request.returns_data)

        if request.weights is None:
            # Equal weights if not provided
            n_assets = len(returns_df.columns)
            weights = np.ones(n_assets) / n_assets
        else:
            weights = np.array(request.weights)

        result = risk_engine.monte_carlo_simulation(
            returns=returns_df,
            weights=weights,
            n_simulations=request.n_simulations,
            n_days=request.n_days
        )

        # Convert numpy arrays to lists for JSON serialization
        result_serializable = {
            "request_id": str(uuid.uuid4()),
            "n_simulations": request.n_simulations,
            "n_days": request.n_days,
            "weights": weights.tolist(),
            "mean_final_value": float(result["mean_final_value"]),
            "std_final_value": float(result["std_final_value"]),
            "percentiles": result["percentiles"]
        }

        return result_serializable

    except Exception as e:
        logger.error(f"Monte Carlo simulation error: {e}")
        raise HTTPException(status_code=500, detail=f"Monte Carlo simulation failed: {str(e)}")


@app.post("/optimize")
async def optimize_portfolio(request: OptimizationRequest) -> Dict[str, Any]:
    """
    Optimize portfolio using specified method.

    Returns optimal weights and portfolio metrics.
    """
    try:
        returns_df = pd.DataFrame(request.returns_data)

        result = risk_engine.optimize_portfolio(
            returns=returns_df,
            method=request.method,
            target_return=request.target_return
        )

        # Convert numpy arrays to lists
        result_serializable = {
            "request_id": str(uuid.uuid4()),
            "method": request.method,
            "weights": result["weights"].tolist() if hasattr(result["weights"], 'tolist') else result["weights"]
        }

        # Add method-specific results
        if "expected_return" in result:
            result_serializable["expected_return"] = float(result["expected_return"])
        if "volatility" in result:
            result_serializable["volatility"] = float(result["volatility"])
        if "sharpe_ratio" in result:
            result_serializable["sharpe_ratio"] = float(result["sharpe_ratio"])

        return result_serializable

    except Exception as e:
        logger.error(f"Portfolio optimization error: {e}")
        raise HTTPException(status_code=500, detail=f"Portfolio optimization failed: {str(e)}")


@app.post("/stress-test")
async def run_stress_test(request: StressTestRequest) -> Dict[str, Any]:
    """
    Run stress testing with predefined scenarios.

    Returns portfolio performance under different stress scenarios.
    """
    try:
        returns_df = pd.DataFrame(request.returns_data)
        weights = np.array(request.weights)

        result = risk_engine.stress_test(
            returns=returns_df,
            weights=weights,
            scenarios=request.scenarios
        )

        return {
            "request_id": str(uuid.uuid4()),
            "weights": weights.tolist(),
            "stress_results": result
        }

    except Exception as e:
        logger.error(f"Stress test error: {e}")
        raise HTTPException(status_code=500, detail=f"Stress test failed: {str(e)}")


@app.get("/methods")
async def get_available_methods() -> Dict[str, List[str]]:
    """Get available risk calculation methods."""
    return {
        "var_methods": ["historical", "parametric", "monte_carlo"],
        "optimization_methods": ["mean_variance", "min_variance", "max_sharpe", "hrp"],
        "confidence_levels": [0.95, 0.99, 0.999]
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8004,
        reload=True,
        log_level="info"
    )