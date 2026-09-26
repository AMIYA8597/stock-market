import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class AutoTradeSetting(Base):
    """Per-user configuration for the automatic paper-trading scan
    (app.tasks.autotrade_tasks.run_autotrade_scan). Disabled by default --
    a user must explicitly opt in. `watchlist_id` points at one of the
    user's existing watchlist tabs (see app.models.watchlist.UserWatchlist)
    so the scanned universe is whatever they already curate there, not a
    separate list to maintain.

    This only ever drives paper orders via BrokerAdapter.place_order, which
    is hardcoded to paper mode -- it does not place real broker orders."""

    __tablename__ = "auto_trade_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    watchlist_id: Mapped[int] = mapped_column(Integer, default=0)
    max_open_positions: Mapped[int] = mapped_column(Integer, default=5)
    risk_per_trade_pct: Mapped[float] = mapped_column(Numeric(5, 4), default=0.02)
    min_confidence: Mapped[float] = mapped_column(Numeric(5, 2), default=65.0)
    last_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_scan_result: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
