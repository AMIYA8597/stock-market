"""
Alerts API endpoints.

Implemented in Phase 8.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

router = APIRouter()


@router.post("/create")
async def create_alert():
    """Create a new alert. (Phase 8)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Alert system not yet implemented — coming in Phase 8",
    )


@router.get("/")
async def list_alerts():
    """List user alerts. (Phase 8)"""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Alert system not yet implemented — coming in Phase 8",
    )
