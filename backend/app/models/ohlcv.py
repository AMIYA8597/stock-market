"""
OHLCV (Open-High-Low-Close-Volume) time-series model.

This table is designed to be converted to a TimescaleDB hypertable
for efficient time-series queries. The hypertable conversion is done
in the Alembic migration via raw SQL:
    SELECT create_hypertable('ohlcv_data', 'timestamp');
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OHLCVData(Base):
    __tablename__ = "ohlcv_data"
    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", "interval", name="uq_ohlcv_symbol_ts_interval"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    interval: Mapped[str] = mapped_column(
        String(10), nullable=False, default="1d",
        comment="1m, 5m, 15m, 1h, 1d, 1wk, 1mo",
    )
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    adjusted_close: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(
        String(30), nullable=False, default="yfinance",
        comment="yfinance | alpha_vantage | nse | coingecko",
    )

    def __repr__(self) -> str:
        return f"<OHLCV(symbol='{self.symbol}', ts='{self.timestamp}', close={self.close})>"
