"""User watchlist model for tracking favorite symbols."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import UUID as SQLA_UUID
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class UserWatchlist(Base):
    """User watchlist tracking favorite symbols.

    Fields:
        id (UUID): Unique watchlist item identifier.
        user_id (UUID): Foreign key to User.
        symbol (str): Ticker symbol.
        added_at (datetime): UTC timestamp when symbol was added.

    Constraints:
        - UNIQUE(user_id, symbol): A user can only have a symbol once in their watchlist.
    """

    __tablename__ = "user_watchlist"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_user_watchlist_user_symbol"),
    )

    id: Mapped[UUID] = mapped_column(
        SQLA_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        doc="Unique identifier",
    )
    user_id: Mapped[UUID] = mapped_column(
        SQLA_UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        doc="Foreign key to users",
    )
    symbol: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Ticker symbol",
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When symbol was added (UTC)",
    )

    def __repr__(self) -> str:
        return f"<UserWatchlist(user_id={self.user_id}, symbol='{self.symbol}')>"
