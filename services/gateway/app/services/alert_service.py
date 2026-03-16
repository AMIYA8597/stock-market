"""
Alert service implementation.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis_client
from app.models.alert import Alert, Notification, Watchlist
from app.schemas.alerts import (
    AlertCreate,
    AlertResponse,
    AlertUpdate,
    NotificationResponse,
    WatchlistCreate,
    WatchlistResponse,
)


class AlertService:
    """Service for handling alerts and notifications."""

    def __init__(self):
        self.redis = get_redis_client()
        self.alert_service_url = "http://alert-service:8004"  # Internal service URL
        self.cache_ttl = 300  # 5 minutes

    async def create_alert(
        self,
        alert_data: AlertCreate,
        user_id: str,
        db: AsyncSession
    ) -> AlertResponse:
        """
        Create a new alert.
        """
        # Create alert in database
        alert = Alert(
            user_id=user_id,
            symbol=alert_data.symbol,
            alert_type=alert_data.alert_type,
            condition_value=alert_data.condition_value,
            message=alert_data.message,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(alert)
        await db.commit()
        await db.refresh(alert)

        # Register alert with alert service
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.alert_service_url}/register",
                    json={
                        "alert_id": str(alert.id),
                        "user_id": user_id,
                        "symbol": alert_data.symbol,
                        "alert_type": alert_data.alert_type,
                        "condition_value": alert_data.condition_value,
                        "message": alert_data.message
                    }
                )
        except Exception as e:
            # Log error but don't fail the creation
            print(f"Failed to register alert with service: {e}")

        return AlertResponse(
            id=str(alert.id),
            user_id=alert.user_id,
            symbol=alert.symbol,
            alert_type=alert.alert_type,
            condition_value=alert.condition_value,
            message=alert.message,
            is_active=alert.is_active,
            triggered_at=None,
            created_at=alert.created_at.isoformat(),
            updated_at=alert.updated_at.isoformat()
        )

    async def get_alerts(
        self,
        user_id: str,
        db: AsyncSession
    ) -> List[AlertResponse]:
        """
        Get user's alerts.
        """
        alerts_result = await db.execute(
            Alert.__table__.select().where(Alert.user_id == user_id)
        )
        alerts = alerts_result.scalars().all()

        responses = []
        for alert in alerts:
            responses.append(AlertResponse(
                id=str(alert.id),
                user_id=alert.user_id,
                symbol=alert.symbol,
                alert_type=alert.alert_type,
                condition_value=alert.condition_value,
                message=alert.message,
                is_active=alert.is_active,
                triggered_at=alert.triggered_at.isoformat() if alert.triggered_at else None,
                created_at=alert.created_at.isoformat(),
                updated_at=alert.updated_at.isoformat()
            ))

        return responses

    async def update_alert(
        self,
        alert_id: str,
        alert_data: AlertUpdate,
        user_id: str,
        db: AsyncSession
    ) -> AlertResponse:
        """
        Update an alert.
        """
        alert = await db.get(Alert, alert_id)
        if not alert or alert.user_id != user_id:
            raise Exception("Alert not found")

        # Update fields
        for field, value in alert_data.dict(exclude_unset=True).items():
            if hasattr(alert, field):
                setattr(alert, field, value)

        alert.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(alert)

        # Update alert service
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.put(
                    f"{self.alert_service_url}/alerts/{alert_id}",
                    json={
                        "alert_type": alert.alert_type,
                        "condition_value": alert.condition_value,
                        "message": alert.message,
                        "is_active": alert.is_active
                    }
                )
        except Exception as e:
            print(f"Failed to update alert in service: {e}")

        return AlertResponse(
            id=str(alert.id),
            user_id=alert.user_id,
            symbol=alert.symbol,
            alert_type=alert.alert_type,
            condition_value=alert.condition_value,
            message=alert.message,
            is_active=alert.is_active,
            triggered_at=alert.triggered_at.isoformat() if alert.triggered_at else None,
            created_at=alert.created_at.isoformat(),
            updated_at=alert.updated_at.isoformat()
        )

    async def delete_alert(
        self,
        alert_id: str,
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, str]:
        """
        Delete an alert.
        """
        alert = await db.get(Alert, alert_id)
        if not alert or alert.user_id != user_id:
            raise Exception("Alert not found")

        # Remove from alert service
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.delete(f"{self.alert_service_url}/alerts/{alert_id}")
        except Exception as e:
            print(f"Failed to delete alert from service: {e}")

        await db.delete(alert)
        await db.commit()

        return {"message": "Alert deleted successfully"}

    async def get_notifications(
        self,
        user_id: str,
        limit: int = 50,
        db: AsyncSession = None
    ) -> List[NotificationResponse]:
        """
        Get user's notifications.
        """
        notifications_result = await db.execute(
            Notification.__table__.select().where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        notifications = notifications_result.scalars().all()

        responses = []
        for notification in notifications:
            responses.append(NotificationResponse(
                id=str(notification.id),
                user_id=notification.user_id,
                type=notification.type,
                title=notification.title,
                message=notification.message,
                data=json.loads(notification.data) if notification.data else {},
                is_read=notification.is_read,
                created_at=notification.created_at.isoformat()
            ))

        return responses

    async def mark_notification_read(
        self,
        notification_id: str,
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, str]:
        """
        Mark notification as read.
        """
        notification = await db.get(Notification, notification_id)
        if not notification or notification.user_id != user_id:
            raise Exception("Notification not found")

        notification.is_read = True
        await db.commit()

        return {"message": "Notification marked as read"}

    async def create_watchlist(
        self,
        watchlist_data: WatchlistCreate,
        user_id: str,
        db: AsyncSession
    ) -> WatchlistResponse:
        """
        Create a watchlist.
        """
        # Create watchlist in database
        watchlist = Watchlist(
            user_id=user_id,
            name=watchlist_data.name,
            description=watchlist_data.description,
            symbols=json.dumps(watchlist_data.symbols),
            is_default=watchlist_data.is_default,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(watchlist)
        await db.commit()
        await db.refresh(watchlist)

        return WatchlistResponse(
            id=str(watchlist.id),
            user_id=watchlist.user_id,
            name=watchlist.name,
            description=watchlist.description,
            symbols=watchlist_data.symbols,
            is_default=watchlist.is_default,
            created_at=watchlist.created_at.isoformat(),
            updated_at=watchlist.updated_at.isoformat()
        )

    async def get_watchlists(
        self,
        user_id: str,
        db: AsyncSession
    ) -> List[WatchlistResponse]:
        """
        Get user's watchlists.
        """
        watchlists_result = await db.execute(
            Watchlist.__table__.select().where(Watchlist.user_id == user_id)
        )
        watchlists = watchlists_result.scalars().all()

        responses = []
        for watchlist in watchlists:
            responses.append(WatchlistResponse(
                id=str(watchlist.id),
                user_id=watchlist.user_id,
                name=watchlist.name,
                description=watchlist.description,
                symbols=json.loads(watchlist.symbols),
                is_default=watchlist.is_default,
                created_at=watchlist.created_at.isoformat(),
                updated_at=watchlist.updated_at.isoformat()
            ))

        return responses

    async def update_watchlist(
        self,
        watchlist_id: str,
        watchlist_data: WatchlistCreate,
        user_id: str,
        db: AsyncSession
    ) -> WatchlistResponse:
        """
        Update a watchlist.
        """
        watchlist = await db.get(Watchlist, watchlist_id)
        if not watchlist or watchlist.user_id != user_id:
            raise Exception("Watchlist not found")

        watchlist.name = watchlist_data.name
        watchlist.description = watchlist_data.description
        watchlist.symbols = json.dumps(watchlist_data.symbols)
        watchlist.is_default = watchlist_data.is_default
        watchlist.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(watchlist)

        return WatchlistResponse(
            id=str(watchlist.id),
            user_id=watchlist.user_id,
            name=watchlist.name,
            description=watchlist.description,
            symbols=json.loads(watchlist.symbols),
            is_default=watchlist.is_default,
            created_at=watchlist.created_at.isoformat(),
            updated_at=watchlist.updated_at.isoformat()
        )

    async def delete_watchlist(
        self,
        watchlist_id: str,
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, str]:
        """
        Delete a watchlist.
        """
        watchlist = await db.get(Watchlist, watchlist_id)
        if not watchlist or watchlist.user_id != user_id:
            raise Exception("Watchlist not found")

        await db.delete(watchlist)
        await db.commit()

        return {"message": "Watchlist deleted successfully"}

    async def get_watchlist_quotes(
        self,
        watchlist_id: str,
        user_id: str,
        db: AsyncSession
    ) -> List[Dict]:
        """
        Get current quotes for all symbols in a watchlist.
        """
        watchlist = await db.get(Watchlist, watchlist_id)
        if not watchlist or watchlist.user_id != user_id:
            raise Exception("Watchlist not found")

        symbols = json.loads(watchlist.symbols)

        # TODO: Batch fetch quotes from market data service
        quotes = []
        for symbol in symbols:
            try:
                # This would call the market data service
                quote = {
                    "symbol": symbol,
                    "price": 100.0,  # Placeholder
                    "change": 2.5,
                    "change_percent": 2.55
                }
                quotes.append(quote)
            except Exception as e:
                print(f"Failed to get quote for {symbol}: {e}")

        return quotes

    async def trigger_alert(
        self,
        alert_id: str,
        trigger_data: Dict,
        db: AsyncSession
    ) -> None:
        """
        Trigger an alert (called by alert service).
        """
        alert = await db.get(Alert, alert_id)
        if not alert:
            return

        # Mark alert as triggered
        alert.triggered_at = datetime.utcnow()
        alert.is_active = False  # One-time alerts

        # Create notification
        notification = Notification(
            user_id=alert.user_id,
            type="alert",
            title=f"Alert Triggered: {alert.symbol}",
            message=alert.message,
            data=json.dumps(trigger_data),
            is_read=False,
            created_at=datetime.utcnow()
        )

        db.add(notification)
        await db.commit()

        # TODO: Send push notification, email, etc.