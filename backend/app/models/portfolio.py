"""Portfolio holdings and transaction models for user position management.

Tracks user holdings and realized/unrealized P&L across all assets.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Numeric, String, UUID as SQLA_UUID, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class PortfolioHolding(Base):
    """User portfolio position in a single symbol.
    
    Fields:
        id (UUID): Unique holding identifier, primary key.
        user_id (UUID): Foreign key to User.
        symbol_id (int): Foreign key to Symbol.
        quantity (Decimal): Number of units held (precision to 8 decimals).
        avg_buy_price (Decimal): Average purchase price per unit.
        realized_pnl (Decimal): Realized profit/loss from closed positions.
        updated_at (datetime): Last update timestamp (UTC).
    
    Constraints:
        - UNIQUE(user_id, symbol_id): One holding per symbol per user.
        - Uses Decimal for financial precision.
        - Foreign keys on user_id and symbol_id for referential integrity.
    """

    __tablename__ = "portfolio_holdings"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol_id", name="uq_portfolio_holding_user_symbol"),
    )

    id: Mapped[UUID] = mapped_column(
        SQLA_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        doc="Unique holding identifier",
    )
    user_id: Mapped[UUID] = mapped_column(
        SQLA_UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        doc="Foreign key to users",
    )
    symbol_id: Mapped[int] = mapped_column(
        ForeignKey("symbols.id"),
        nullable=False,
        index=True,
        doc="Foreign key to symbols",
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        doc="Number of units held",
    )
    avg_buy_price: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        doc="Average purchase price per unit",
    )
    realized_pnl: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Realized P&L from closed positions",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Last update timestamp (UTC)",
    )

    def __repr__(self) -> str:
        return f"<PortfolioHolding(user_id={self.user_id}, symbol_id={self.symbol_id}, qty={self.quantity})>"
