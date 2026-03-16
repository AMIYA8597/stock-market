"""OHLCV model for Data Pipeline Service."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ

from app.core.database import Base


class OHLCV(Base):
    """OHLCV time-series data."""

    __tablename__ = "ohlcv"

    time = Column(TIMESTAMPTZ, nullable=False, primary_key=True)
    symbol = Column(Text, nullable=False, primary_key=True)
    exchange = Column(Text, nullable=False, primary_key=True)
    open = Column(Numeric(18, 4), nullable=False)
    high = Column(Numeric(18, 4), nullable=False)
    low = Column(Numeric(18, 4), nullable=False)
    close = Column(Numeric(18, 4), nullable=False)
    volume = Column(BigInteger, nullable=False)