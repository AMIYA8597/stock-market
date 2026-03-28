"""Trade transaction history model.

Buy/sell transactions with brokerage fees, taxes, and net amount computed.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Numeric, String, UUID as SQLA_UUID, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Transaction(Base):
    """Trade transaction (buy/sell) with costs and tax.

    Fields:
        id (UUID): Unique transaction identifier, primary key.
        user_id (UUID): Foreign key to User.
        symbol_id (int): Foreign key to Symbol.
        type (str): Transaction type (BUY or SELL).
        quantity (Decimal): Number of units traded (precision to 8 decimals).
        price (Decimal): Price per unit at execution (precision to 8 decimals).
        brokerage (Decimal): Brokerage fees paid (precision to 4 decimals).
        stt (Decimal): Securities Transaction Tax paid (precision to 4 decimals).
        net_amount (Decimal): Quantity x Price +/- Fees +/- Tax (precision to 4 decimals).
        timestamp (datetime): Transaction execution time (UTC).
    """

    __tablename__ = "transactions"

    id: Mapped[UUID] = mapped_column(
        SQLA_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        doc="Unique transaction identifier",
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
    type: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        doc="Transaction type (BUY or SELL)",
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        doc="Number of units traded",
    )
    price: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        doc="Price per unit at execution",
    )
    brokerage: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Brokerage fees paid",
    )
    stt: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        default=Decimal("0"),
        nullable=False,
        doc="Securities Transaction Tax paid",
    )
    net_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 4),
        nullable=False,
        doc="Quantity x Price +/- Fees +/- Tax",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        doc="Transaction execution timestamp (UTC)",
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction(user_id={self.user_id}, symbol_id={self.symbol_id}, "
            f"type='{self.type}', qty={self.quantity})>"
        )
