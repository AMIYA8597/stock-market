"""
Market data API endpoints.

Implemented in Phase 2 with real data pipeline integration.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

router = APIRouter()


@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Get real-time quote for a symbol. (Phase 2)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Market data pipeline not yet implemented — coming in Phase 2",
    )


@router.get("/history/{symbol}")
async def get_history(
    symbol: str,
    interval: str = Query(default="1d", pattern="^(1m|5m|15m|1h|1d|1wk|1mo)$"),
    period: str = Query(default="2y"),
):
    """Get historical OHLCV data. (Phase 2)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Market data pipeline not yet implemented — coming in Phase 2",
    )
