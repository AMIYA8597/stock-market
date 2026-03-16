"""
Market data models.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class OHLCV(Base):
    """
    OHLCV data model for time-series market data.
    """
    __tablename__ = "ohlcv"

    time = Column(DateTime(timezone=True), primary_key=True)
    symbol = Column(String(20), primary_key=True, index=True)
    exchange = Column(String(10), primary_key=True)
    open = Column(Numeric(18, 4), nullable=False)
    high = Column(Numeric(18, 4), nullable=False)
    low = Column(Numeric(18, 4), nullable=False)
    close = Column(Numeric(18, 4), nullable=False)
    volume = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<OHLCV(symbol={self.symbol}, time={self.time}, close={self.close})>"


class TickData(Base):
    """
    Tick-level market data for microstructure analysis.
    """
    __tablename__ = "tick_data"

    time = Column(DateTime(timezone=True), primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    price = Column(Numeric(18, 4))
    volume = Column(Integer)
    side = Column(String(4))  # BUY, SELL
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<TickData(symbol={self.symbol}, time={self.time}, price={self.price}, side={self.side})>"


class Prediction(Base):
    """
    ML model predictions storage.
    """
    __tablename__ = "predictions"

    id = Column(String(64), primary_key=True)  # Composite key: symbol + model + timestamp
    symbol = Column(String(20), nullable=False, index=True)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=False)
    prediction_time = Column(DateTime(timezone=True), nullable=False, index=True)
    horizon_days = Column(Integer, nullable=False)
    predicted_price = Column(Numeric(18, 4))
    predicted_direction = Column(Integer)  # +1, -1, 0
    confidence = Column(Numeric(5, 4))
    lower_80 = Column(Numeric(18, 4))
    upper_80 = Column(Numeric(18, 4))
    lower_95 = Column(Numeric(18, 4))
    upper_95 = Column(Numeric(18, 4))
    feature_importances = Column(Text)  # JSON string
    actual_price = Column(Numeric(18, 4))  # Filled after realization
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Prediction(symbol={self.symbol}, model={self.model_name}, direction={self.predicted_direction})>"


class MarketIndex(Base):
    """
    Market index data (Nifty50, Sensex, etc.).
    """
    __tablename__ = "market_indices"

    time = Column(DateTime(timezone=True), primary_key=True)
    symbol = Column(String(20), primary_key=True, index=True)
    value = Column(Numeric(18, 4), nullable=False)
    change = Column(Numeric(18, 4))
    change_percent = Column(Numeric(7, 4))
    volume = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<MarketIndex(symbol={self.symbol}, time={self.time}, value={self.value})>"


class EconomicIndicator(Base):
    """
    Economic indicators (GDP, inflation, interest rates, etc.).
    """
    __tablename__ = "economic_indicators"

    time = Column(DateTime(timezone=True), primary_key=True)
    indicator = Column(String(100), primary_key=True, index=True)
    value = Column(Numeric(18, 4), nullable=False)
    unit = Column(String(20))
    source = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<EconomicIndicator(indicator={self.indicator}, time={self.time}, value={self.value})>"