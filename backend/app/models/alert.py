"""Alert model for user-configurable market alerts."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="price_cross | rsi_threshold | ml_signal | sentiment_spike | volume_anomaly",
    )
    condition_json: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment='Alert condition as JSON, e.g. {"operator": "gt", "value": 150.0}',
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notification_method: Mapped[str] = mapped_column(
        String(20), nullable=False, default="in_app",
        comment="in_app | email | both",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="alerts")

    def __repr__(self) -> str:
        return f"<Alert(symbol='{self.symbol}', type='{self.alert_type}', triggered={self.is_triggered})>"
