"""
Backtesting API endpoints.

Implemented in Phase 4 with custom backtesting engine.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.schemas.backtest import BacktestRequest

router = APIRouter()


@router.post("/run")
async def run_backtest(payload: BacktestRequest):
    """Run a strategy backtest. (Phase 4)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Backtesting engine not yet implemented — coming in Phase 4",
    )


@router.get("/results")
async def list_backtest_results():
    """List previous backtest results. (Phase 4)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Backtesting engine not yet implemented — coming in Phase 4",
    )
