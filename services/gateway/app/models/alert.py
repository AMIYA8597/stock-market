"""
Alert and notification models.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, UUID
from sqlalchemy.sql import func

from app.core.database import Base


class Alert(Base):
    """
    Alert configuration model.
    """
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    condition = Column(String(100), nullable=False)  # price_above, price_below, etc.
    threshold = Column(Integer, nullable=False)  # In paisa
    is_active = Column(Boolean, default=True, nullable=False)
    notification_channels = Column(String(255), default="in_app")  # comma-separated
    last_triggered_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Alert(id={self.id}, symbol={self.symbol}, condition={self.condition})>"


class AlertTrigger(Base):
    """
    Alert trigger history.
    """
    __tablename__ = "alert_triggers"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    alert_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    triggered_at = Column(DateTime(timezone=True), nullable=False, index=True)
    trigger_value = Column(Integer, nullable=False)  # Actual value that triggered alert
    message = Column(Text, nullable=False)
    notification_sent = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<AlertTrigger(id={self.id}, alert_id={self.alert_id}, triggered_at={self.triggered_at})>"


class Notification(Base):
    """
    User notifications.
    """
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # alert, prediction, system
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    action_url = Column(String(500))  # URL to navigate to when clicked
    metadata = Column(Text)  # JSON string with additional data
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.type}, is_read={self.is_read})>"


class Watchlist(Base):
    """
    User watchlist for tracking favorite stocks.
    """
    __tablename__ = "watchlists"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    symbols = Column(Text, nullable=False)  # JSON array of symbols
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<Watchlist(id={self.id}, name={self.name}, user_id={self.user_id})>"