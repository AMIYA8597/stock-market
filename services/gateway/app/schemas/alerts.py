"""
Pydantic schemas for alerts endpoints.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

class AlertBase(BaseModel):
    """Base alert schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Alert name")
    symbol: str = Field(..., min_length=1, max_length=20, description="Stock symbol")
    condition: str = Field(..., description="Alert condition")
    threshold: int = Field(..., description="Alert threshold in paisa")
    notification_channels: str = Field(
        default="in_app",
        description="Comma-separated notification channels (in_app,email,webhook)"
    )

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v):
        """Validate stock symbol format."""
        import re
        if not re.match(r'^[A-Z0-9.-]{1,20}$', v):
            raise ValueError("Invalid symbol format")
        return v.upper()

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, v):
        """Validate alert condition."""
        valid_conditions = [
            "price_above", "price_below", "price_change_percent",
            "volume_above", "rsi_above", "rsi_below",
            "macd_crossover", "bollinger_breakout",
            "moving_average_crossover", "support_break",
            "resistance_break", "gap_up", "gap_down"
        ]
        if v not in valid_conditions:
            raise ValueError(f"Invalid condition. Must be one of: {', '.join(valid_conditions)}")
        return v

    @field_validator("notification_channels")
    @classmethod
    def validate_channels(cls, v):
        """Validate notification channels."""
        valid_channels = ["in_app", "email", "webhook", "sms"]
        channels = [c.strip() for c in v.split(",")]
        for channel in channels:
            if channel not in valid_channels:
                raise ValueError(f"Invalid channel: {channel}")
        return ",".join(channels)

class AlertCreate(AlertBase):
    """Alert creation schema."""
    pass


class AlertUpdate(BaseModel):
    """Alert update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    condition: Optional[str] = None
    threshold: Optional[int] = None
    notification_channels: Optional[str] = None
    is_active: Optional[bool] = None


class AlertResponse(AlertBase):
    """Alert response schema."""
    id: str
    user_id: str
    is_active: bool
    last_triggered_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertTriggerResponse(BaseModel):
    """Alert trigger response."""
    id: str
    alert_id: str
    triggered_at: datetime
    trigger_value: int
    message: str
    notification_sent: bool

    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    """Notification response."""
    id: str
    user_id: str
    type: str
    title: str
    message: str
    is_read: bool
    action_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class WatchlistCreate(BaseModel):
    """Watchlist creation schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Watchlist name")
    symbols: List[str] = Field(..., min_items=1, max_items=100, description="List of symbols")

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, v):
        """Validate symbol formats."""
        import re
        for symbol in v:
            if not re.match(r'^[A-Z0-9.-]{1,20}$', symbol):
                raise ValueError(f"Invalid symbol format: {symbol}")
        return [s.upper() for s in v]


class WatchlistUpdate(BaseModel):
    """Watchlist update schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    symbols: Optional[List[str]] = None


class WatchlistResponse(BaseModel):
    """Watchlist response."""
    id: str
    user_id: str
    name: str
    symbols: List[str]
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertStatsResponse(BaseModel):
    """Alert statistics response."""
    total_alerts: int
    active_alerts: int
    triggered_today: int
    notifications_sent_today: int
    most_triggered_symbol: Optional[str]
    most_triggered_condition: Optional[str]


class AlertsResponse(BaseModel):
    """Generic alerts response."""
    success: bool
    message: str
    data: Optional[dict] = None