"""Final ensemble trading signals model.

Combined signal from all ML models with direction, confidence, and Kelly sizing.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Numeric, String, Integer, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class EnsembleSignal(Base):
    """Final ensemble trading signal (combined from all models).
    
    Fields:
        time (datetime): Signal timestamp (UTC), primary key.
        symbol_id (int): Foreign key to Symbol, primary key.
        signal (Decimal): Final continuous signal in range [-1, +1].
        confidence (Decimal): Ensemble confidence/agreement in range [0, 1].
        direction (str): Discrete direction (STRONG_BUY, BUY, NEUTRAL, SELL, STRONG_SELL).
        model_weights (dict): Per-model weights in ensemble: {model_name: weight}.
        regime_state (int): Current HMM regime state (0=bull, 1=bear, 2=sideways, 3=crisis).
        kelly_fraction (Decimal): Position sizing fraction using Kelly criterion.
    
    Primary Key: (time, symbol_id)
    Indexes: Implicit on primary key columns
    
    Direction Mapping:
        signal < -0.6 -> STRONG_SELL
        -0.6 <= signal < -0.2 -> SELL
        -0.2 <= signal <= 0.2 -> NEUTRAL
        0.2 < signal <= 0.6 -> BUY
        signal > 0.6 -> STRONG_BUY
    """

    __tablename__ = "ensemble_signals"
    __table_args__ = (
        UniqueConstraint("time", "symbol_id", name="uq_ensemble_signal_time_symbol"),
    )

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        primary_key=True,
        doc="Signal timestamp (UTC)",
    )
    symbol_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("symbols.id"),
        nullable=False,
        primary_key=True,
        doc="Foreign key to symbols",
    )
    signal: Mapped[Decimal] = mapped_column(
        Numeric(6, 4),
        nullable=False,
        doc="Final continuous signal [-1, +1]",
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        doc="Ensemble confidence [0, 1]",
    )
    direction: Mapped[str] = mapped_column(
        String(12),
        nullable=False,
        doc="Direction (STRONG_BUY, BUY, NEUTRAL, SELL, STRONG_SELL)",
    )
    model_weights: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        doc="Per-model weights: {model_name: weight}",
    )
    regime_state: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="HMM regime state (0=bull, 1=bear, 2=sideways, 3=crisis)",
    )
    kelly_fraction: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
        doc="Kelly criterion position sizing fraction",
    )

    def __repr__(self) -> str:
        return f"<EnsembleSignal(symbol_id={self.symbol_id}, time='{self.time}', direction='{self.direction}', confidence={self.confidence})>"
