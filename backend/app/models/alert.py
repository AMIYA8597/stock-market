"""User-configurable trading alerts model.

Alerts can be price-based, volume-based, sentiment-based, or ML signal-based.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import UUID as SQLA_UUID
from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Alert(Base):
    """User-configurable market alert.

    Fields:
        id (UUID): Unique alert identifier, primary key.
        user_id (UUID): Foreign key to User.
        symbol_id (int): Foreign key to Symbol (nullable for portfolio-level alerts).
        alert_type (str): Alert category (PRICE_ABOVE, PRICE_BELOW, RSI_OB, etc.).
        threshold (Decimal): Numeric threshold value for comparison.
        is_triggered (bool): Whether alert has been triggered.
        triggered_at (datetime): When alert was triggered (nullable).
        created_at (datetime): When alert was created (UTC).

    Alert Types:
        - PRICE_ABOVE / PRICE_BELOW: Price levels
        - RSI_OB / RSI_OS: RSI overbought/oversold
        - MACD_CROSS: MACD indicator crossover
        - SIGNAL_CHANGE: ML signal direction change
        - REGIME_CHANGE: HMM regime state transition
    """

    __tablename__ = "alerts"

    id: Mapped[UUID] = mapped_column(
        SQLA_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        doc="Unique alert identifier",
    )
    user_id: Mapped[UUID] = mapped_column(
        SQLA_UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
        doc="Foreign key to users",
    )
    symbol_id: Mapped[int | None] = mapped_column(
        ForeignKey("symbols.id"),
        nullable=True,
        index=True,
        doc="Foreign key to symbols (nullable for portfolio-level)",
    )
    alert_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        doc="Alert type (PRICE_ABOVE, PRICE_BELOW, RSI_OB, MACD_CROSS, SIGNAL_CHANGE, REGIME_CHANGE)",
    )
    threshold: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8),
        nullable=True,
        doc="Numeric threshold for comparison",
    )
    is_triggered: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether alert has been triggered",
    )
    triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When alert was last triggered",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Created timestamp (UTC)",
    )

    def __repr__(self) -> str:
        return f"<Alert(user_id={self.user_id}, type='{self.alert_type}', triggered={self.is_triggered})>"
