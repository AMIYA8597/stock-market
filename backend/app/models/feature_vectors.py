"""Feature vector store (TimescaleDB hypertable).

Computed features for all symbols across all timestamps.
Features are computed by the feature engineering pipeline and stored
as JSONB for flexible schema evolution.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, JSON, ForeignKey, UniqueConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class FeatureVector(Base):
    """Feature vector store (TimescaleDB hypertable).
    
    Fields:
        time (datetime): Feature timestamp (hypertable time column), primary key.
        symbol_id (int): Foreign key to Symbol, primary key.
        features (dict): 80+ computed float features as JSONB.
        feature_version (str): Feature version ID for schema tracking (v1, v2, etc.).
    
    Primary Key: (time, symbol_id)
    Hypertable: Will be converted in migration 002
    Indexes: (symbol_id, time DESC) for fast range queries
    
    Feature Naming Convention:
        - price_factors: log_return, momentum_10d, high_52w, drawdown_from_high
        - volatility_factors: parkinson_vol, garch_vol, vol_of_vol
        - microstructure: order_flow_imbalance, amihud_lambda, bid_ask_spread
        - calendar: day_of_week, month_of_year (sin/cos encoded)
        - cross_sectional: z_score, rank_percentile, sector_relative
        - sentiment: finbert_score, news_volume
        - factor_betas: mkt_beta, smb_beta, hml_beta, rmw_beta, cma_beta
    
    Schema Evolution:
        - feature_version tracks schema version for backward compatibility
        - Features are added/removed via migration with version bump
    """

    __tablename__ = "feature_vectors"
    __table_args__ = (
        UniqueConstraint("time", "symbol_id", name="uq_feature_vector_time_symbol"),
    )

    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        primary_key=True,
        doc="Feature timestamp (hypertable time column)",
    )
    symbol_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("symbols.id"),
        nullable=False,
        primary_key=True,
        doc="Foreign key to symbols",
    )
    features: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        doc="80+ computed float features keyed by factor name",
    )
    feature_version: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="v1",
        doc="Feature schema version for tracking",
    )

    def __repr__(self) -> str:
        return f"<FeatureVector(symbol_id={self.symbol_id}, time='{self.time}', version='{self.feature_version}')>"
