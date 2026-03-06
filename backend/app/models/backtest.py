"""Backtest result model storing strategy performance metrics."""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    strategy_name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    params_json: Mapped[str] = mapped_column(Text, nullable=False, comment="Strategy parameters as JSON")
    symbols_json: Mapped[str] = mapped_column(Text, nullable=False, comment="Symbols used in backtest")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    benchmark: Mapped[str] = mapped_column(String(20), nullable=False, default="^NSEI")

    # ─── Performance Metrics ───────────────────────────────
    total_return: Mapped[float] = mapped_column(Float, nullable=False)
    cagr: Mapped[float] = mapped_column(Float, nullable=False, comment="Compound Annual Growth Rate")
    sharpe_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    sortino_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=False)
    calmar_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    win_rate: Mapped[float] = mapped_column(Float, nullable=False)
    profit_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False)

    # ─── Full Results ──────────────────────────────────────
    results_json: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Complete backtest results including equity curve, trade log, etc.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user = relationship("User", back_populates="backtest_results")

    def __repr__(self) -> str:
        return (
            f"<Backtest(strategy='{self.strategy_name}', sharpe={self.sharpe_ratio}, "
            f"cagr={self.cagr})>"
        )
