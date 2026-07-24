"""Instrument model representing tradeable assets and forming the canonical symbol universe."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Instrument(Base):
    """Tradeable instrument metadata and canonical symbol universe.

    Fields:
        id (int): Serial primary key.
        symbol (str): Clean ticker symbol (e.g., RELIANCE).
        display_name (str): Human-readable name.
        exchange (str): Exchange where asset trades (e.g., NSE).
        yfinance_ticker (str): Suffix-appended ticker for yfinance (e.g., RELIANCE.NS).
        is_active (bool): Whether symbol is actively traded and updated.
        created_at (datetime): Timestamp when symbol was added.
    """

    __tablename__ = "instrument"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Serial primary key",
    )
    symbol: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
        doc="Clean ticker symbol (e.g., RELIANCE)",
    )
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Human-readable name of the asset",
    )
    exchange: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="Exchange (NSE, BSE, NYSE, NASDAQ, CRYPTO)",
    )
    yfinance_ticker: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="yfinance compatible ticker",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        doc="Actively traded and updated",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when symbol was added",
    )

    @classmethod
    def normalize_symbol(cls, raw_symbol: str) -> str:
        """Strip suffix from raw symbol to get the canonical symbol."""
        return raw_symbol.replace(".NS", "").replace(".BO", "").upper()

    def __repr__(self) -> str:
        return f"<Instrument(id={self.id}, symbol='{self.symbol}', display_name='{self.display_name}')>"
