"""
Stock screener API endpoints.

Implemented in Phase 2 with market data + Phase 3 for ML filters.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.get("/")
async def run_screener():
    """Screen stocks by technical, fundamental, and ML criteria. (Phase 2)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Screener not yet implemented — coming in Phase 2",
    )
