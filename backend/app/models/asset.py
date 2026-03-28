"""Symbol/Asset model representing tradeable instruments across all asset classes.

Stores metadata for all tradeable symbols: equities, crypto, indexes, ETFs, forex.
Symbols are the master reference for all time-series and feature data.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Symbol(Base):
    """Tradeable instrument metadata.
    
    Fields:
        id (int): Serial primary key, used as foreign key in time-series tables.
        ticker (str): Unique ticker symbol (e.g., RELIANCE.NS, AAPL, BTC-USD).
        name (str): Human-readable name of the asset.
        exchange (str): Exchange where asset trades (NSE, BSE, NYSE, NASDAQ, CRYPTO).
        sector (str): Economic sector classification.
        industry (str): Industry classification within sector.
        market_cap_bucket (str): Market cap category (LARGE, MID, SMALL, MICRO).
        asset_type (str): Classification (EQUITY, CRYPTO, INDEX, ETF, FOREX).
        currency (str): Currency of price quotes (USD, INR, etc.).
        is_active (bool): Whether symbol is actively traded and updated.
        created_at (datetime): Timestamp when symbol was added to database.
    
    Constraints:
        - ticker is globally unique.
        - All timestamps are UTC timezone-aware.
        - Inactive symbols are excluded from real-time updates but retained for history.
    """

    __tablename__ = "symbols"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        doc="Serial primary key for foreign key references",
    )
    ticker: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique ticker symbol (e.g., RELIANCE.NS, AAPL, BTC-USD)",
    )
    name: Mapped[str] = mapped_column(
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
    sector: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="Economic sector classification",
    )
    industry: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        doc="Industry classification within sector",
    )
    market_cap_bucket: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        doc="Market cap category (LARGE, MID, SMALL, MICRO)",
    )
    asset_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        index=True,
        doc="Classification (EQUITY, CRYPTO, INDEX, ETF, FOREX)",
    )
    currency: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="USD",
        doc="Currency of price quotes",
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

    def __repr__(self) -> str:
        return f"<Symbol(id={self.id}, ticker='{self.ticker}', name='{self.name}')>"
