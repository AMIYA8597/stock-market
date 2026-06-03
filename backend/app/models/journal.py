"""Trade journal model to log manual review notes, emotions, and trade tags.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import UUID as SQLA_UUID
from sqlalchemy import DateTime, ForeignKey, Numeric, String, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class TradeJournal(Base):
    """Trade journal entry for logging trade notes, ratings, and tags.

    Fields:
        id (UUID): Unique journal entry identifier, primary key.
        user_id (UUID): Foreign key to User.
        symbol (str): Ticker symbol or instrument name.
        notes (str): Trade log notes, mental state, and strategy review.
        tags (str): Comma-separated strategy tags.
        rating (int): Confidence or strategy star rating (1-5).
        entry_price (Decimal): Entry execution price.
        exit_price (Decimal): Exit execution price.
        quantity (Decimal): Position size or contract size.
        direction (str): Trade direction (LONG or SHORT).
        created_at (datetime): Date when entry was created (UTC).
    """

    __tablename__ = "trade_journals"

    id: Mapped[UUID] = mapped_column(
        SQLA_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        doc="Unique journal entry identifier",
    )
    user_id: Mapped[UUID] = mapped_column(
        SQLA_UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        doc="Foreign key to users",
    )
    symbol: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="Ticker symbol or instrument name",
    )
    notes: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
        default="",
        doc="Trade review notes and comments",
    )
    tags: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Comma-separated strategy tags",
    )
    rating: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Star rating (1 to 5)",
    )
    entry_price: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8),
        nullable=True,
        doc="Entry price",
    )
    exit_price: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8),
        nullable=True,
        doc="Exit price",
    )
    quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8),
        nullable=True,
        doc="Position size / quantity",
    )
    direction: Mapped[str | None] = mapped_column(
        String(8),
        nullable=True,
        doc="LONG or SHORT",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Journal creation timestamp (UTC)",
    )

    def __repr__(self) -> str:
        return f"<TradeJournal(user_id={self.user_id}, symbol='{self.symbol}', rating={self.rating})>"
