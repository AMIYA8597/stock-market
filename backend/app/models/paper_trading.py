"""SQLAlchemy ORM models for Paper Trading.

Tracks virtual account balance, open positions, and executed/pending orders.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import UUID as SQLA_UUID
from sqlalchemy import DateTime, Date, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class PaperWallet(Base):
    """Virtual paper trading wallet for tracking user capital."""

    __tablename__ = "paper_wallets"

    id: Mapped[UUID] = mapped_column(
        SQLA_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        doc="Unique wallet identifier",
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Username or email or user UUID",
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        default=Decimal("100000.00"),
        nullable=False,
        doc="Cash balance available to trade",
    )
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        default=Decimal("0.00"),
        nullable=False,
        doc="Total realized P&L across all closed positions",
    )
    daily_loss_limit: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        default=Decimal("5000.00"),
        nullable=False,
        doc="Maximum allowed loss per day",
    )
    last_reset_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        doc="Last date when daily realized loss was checked or reset",
    )
    daily_realized_loss: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        default=Decimal("0.00"),
        nullable=False,
        doc="Accumulated realized loss for the current day",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Last updated timestamp",
    )

    def __repr__(self) -> str:
        return f"<PaperWallet(user_id='{self.user_id}', balance={self.balance})>"


class PaperPosition(Base):
    """User open positions in paper trading mode."""

    __tablename__ = "paper_positions"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", name="uq_paper_position_user_symbol"),
    )

    id: Mapped[UUID] = mapped_column(
        SQLA_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        doc="Unique position identifier",
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Owner of the position",
    )
    symbol: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="Ticker symbol (e.g. RELIANCE.NS, BTC-USD)",
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        doc="Quantity of shares or units held",
    )
    avg_buy_price: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        doc="Weighted average buy price",
    )
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        default=Decimal("0.00"),
        nullable=False,
        doc="Realized P&L from partial exits of this position",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Last updated timestamp",
    )

    def __repr__(self) -> str:
        return f"<PaperPosition(user_id='{self.user_id}', symbol='{self.symbol}', qty={self.quantity})>"


class PaperOrder(Base):
    """Order logs and history for paper trading."""

    __tablename__ = "paper_orders"

    id: Mapped[UUID] = mapped_column(
        SQLA_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        doc="Unique order identifier",
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Owner of the order",
    )
    symbol: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="Ticker symbol",
    )
    side: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        doc="Transaction side (BUY or SELL)",
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        doc="Quantity ordered",
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        doc="Execution price (or target limit price)",
    )
    order_type: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        doc="Order type (MARKET or LIMIT)",
    )
    limit_price: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8),
        nullable=True,
        doc="Trigger price for limit order",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        default="PENDING",
        nullable=False,
        doc="Status (PENDING, FILLED, CANCELLED)",
    )
    brokerage: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.00"),
        nullable=False,
        doc="Brokerage fee paid",
    )
    stt: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.00"),
        nullable=False,
        doc="Securities Transaction Tax paid",
    )
    slippage: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0.00"),
        nullable=False,
        doc="Slippage amount modeled",
    )
    net_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        doc="Net amount debited/credited (qty * price +/- friction)",
    )
    signal_relation: Mapped[str | None] = mapped_column(
        String(32),
        default="INDEPENDENT",
        nullable=True,
        doc="Relationship of order to system's signal at time of placement (AGREEMENT, AGAINST, INDEPENDENT)",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        doc="Order timestamp (UTC)",
    )

    def __repr__(self) -> str:
        return f"<PaperOrder(user_id='{self.user_id}', symbol='{self.symbol}', side='{self.side}', status='{self.status}')>"
