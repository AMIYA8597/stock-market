"""
Alerts and notifications endpoints.
"""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user_with_permissions
from app.core.database import get_db
from app.schemas.alerts import (
    AlertCreate,
    AlertResponse,
    AlertUpdate,
    NotificationResponse,
    WatchlistCreate,
    WatchlistResponse,
)
from app.services.alert_service import AlertService

router = APIRouter()
alert_service = AlertService()


@router.post("/alerts", response_model=AlertResponse)
async def create_alert(
    alert_data: AlertCreate,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new alert.
    """
    return await alert_service.create_alert(alert_data, current_user["user_id"], db)


@router.get("/alerts", response_model=List[AlertResponse])
async def list_alerts(
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    List user alerts.
    """
    return await alert_service.get_alerts(current_user["user_id"], db)


@router.put("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    alert_data: AlertUpdate,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an alert.
    """
    return await alert_service.update_alert(alert_id, alert_data, current_user["user_id"], db)


@router.delete("/alerts/{alert_id}")
async def delete_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an alert.
    """
    return await alert_service.delete_alert(alert_id, current_user["user_id"], db)


@router.get("/notifications", response_model=List[NotificationResponse])
async def list_notifications(
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    List user notifications.
    """
    return await alert_service.get_notifications(current_user["user_id"], db)


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark notification as read.
    """
    return await alert_service.mark_notification_read(notification_id, current_user["user_id"], db)


@router.post("/watchlists", response_model=WatchlistResponse)
async def create_watchlist(
    watchlist_data: WatchlistCreate,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a watchlist.
    """
    return await alert_service.create_watchlist(watchlist_data, current_user["user_id"], db)


@router.get("/watchlists", response_model=List[WatchlistResponse])
async def list_watchlists(
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    List user watchlists.
    """
    return await alert_service.get_watchlists(current_user["user_id"], db)


@router.put("/watchlists/{watchlist_id}", response_model=WatchlistResponse)
async def update_watchlist(
    watchlist_id: str,
    watchlist_data: WatchlistCreate,  # Using same schema for update
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a watchlist.
    """
    return await alert_service.update_watchlist(watchlist_id, watchlist_data, current_user["user_id"], db)


@router.delete("/watchlists/{watchlist_id}")
async def delete_watchlist(
    watchlist_id: str,
    current_user: dict = Depends(get_current_user_with_permissions),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a watchlist.
    """
    return await alert_service.delete_watchlist(watchlist_id, current_user["user_id"], db)