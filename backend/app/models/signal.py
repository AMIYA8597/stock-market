"""Trading signal model for strategy-generated buy/sell/exit signals."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TradingSignal(Base):
    __tablename__ = "trading_signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    strategy_name: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="mean_reversion | momentum | volatility_breakout | ml_alpha | stat_arb",
    )
    signal_type: Mapped[str] = mapped_column(
        String(10), nullable=False,
        comment="long | short | exit",
    )
    strength: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Signal strength/conviction 0.0 to 1.0",
    )
    price_at_signal: Mapped[float] = mapped_column(Float, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(
        String(2000), nullable=True,
        comment="Additional signal context as JSON string",
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<Signal(symbol='{self.symbol}', strategy='{self.strategy_name}', "
            f"type='{self.signal_type}', strength={self.strength})>"
        )
