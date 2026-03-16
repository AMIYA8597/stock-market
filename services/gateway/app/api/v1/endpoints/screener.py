"""
Stock screener endpoints.
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user_with_permissions
from app.core.database import get_db
from app.schemas.screener import (
    SavedScreenCreate,
    SavedScreenResponse,
    ScreenerRequest,
    ScreenerResponse,
    ScreenerStatsResponse,
)
from app.services.screener_service import ScreenerService

router = APIRouter()
screener_service = ScreenerService()


@router.post("/screen", response_model=ScreenerResponse)
async def screen_stocks(
    screener_data: ScreenerRequest,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Screen stocks based on filters.
    """
    return await screener_service.screen_stocks(screener_data, current_user["user_id"], db)


@router.get("/stats", response_model=ScreenerStatsResponse)
async def get_screener_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Get screener statistics.
    """
    return await screener_service.get_screener_stats(db)


@router.post("/saved", response_model=SavedScreenResponse)
async def save_screen(
    screen_data: SavedScreenCreate,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Save a stock screen.
    """
    return await screener_service.save_screen(screen_data, current_user["user_id"], db)


@router.get("/saved", response_model=List[SavedScreenResponse])
async def list_saved_screens(
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    List saved screens.
    """
    return await screener_service.get_saved_screens(current_user["user_id"], db)