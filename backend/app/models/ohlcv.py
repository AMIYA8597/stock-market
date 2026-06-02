"""OHLCV (Open-High-Low-Close-Volume) time-series model.

Time-series candlestick data for all symbols across multiple intervals.
Designed as a TimescaleDB hypertable for efficient time-series operations.
Conversion to hypertable is done in Alembic migration 002.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class OHLCV(Base):
    """OHLCV candlestick data (TimescaleDB hypertable).

    Fields:
        time (datetime): Candlestick timestamp (hypertable time column), PK.
        symbol_id (int): Foreign key to Symbol, PK.
        open (Decimal): Opening price (64-bit, 8 decimal places).
        high (Decimal): High price (64-bit, 8 decimal places).
        low (Decimal): Low price (64-bit, 8 decimal places).
        close (Decimal): Closing price (64-bit, 8 decimal places).
        volume (Decimal): Trade volume in units (96-bit, 4 decimal places).
        adjusted_close (Decimal): Adjusted close price (optional, 64-bit).
        interval (str): Timeframe (1m, 5m, 15m, 1h, 1d), PK.

    Primary Key: (time, symbol_id, interval)
    Hypertable: Will be converted in migration 002
    Indexes: (symbol_id, time DESC) for fast range queries

    Constraints:
        - Uses Decimal for financial precision (no float rounding).
        - Time column partitioned hourly/daily by TimescaleDB.
        - Foreign key on symbol_id for referential integrity.
    """

    __tablename__ = "ohlcv"
    __table_args__ = (
        UniqueConstraint("time", "symbol_id", "interval", name="uq_ohlcv_time_symbol_interval"),
    )

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        primary_key=True,
        doc="Candlestick timestamp (hypertable time column)",
    )
    symbol_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("symbols.id"),
        nullable=False,
        primary_key=True,
        doc="Foreign key to symbols table",
    )
    open: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        doc="Opening price (NUMERIC for precision)",
    )
    high: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        doc="High price",
    )
    low: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        doc="Low price",
    )
    close: Mapped[Decimal] = mapped_column(
        Numeric(20, 8),
        nullable=False,
        doc="Closing price",
    )
    volume: Mapped[Decimal] = mapped_column(
        Numeric(24, 4),
        nullable=False,
        doc="Trade volume in units",
    )
    adjusted_close: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8),
        nullable=True,
        doc="Adjusted closing price (optional)",
    )
    interval: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        primary_key=True,
        doc="Timeframe (1m, 5m, 15m, 1h, 1d)",
    )

    def __repr__(self) -> str:
        return f"<OHLCV(symbol_id={self.symbol_id}, time='{self.time}', close={self.close}, interval='{self.interval}')>"
