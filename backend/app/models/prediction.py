"""ML model predictions and quantile forecasts.

Per-model predictions including confidence intervals and SHAP explanations.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Numeric, String, Integer, BigInteger, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class MLPrediction(Base):
    """ML model prediction with quantile forecasts and explanations.
    
    Fields:
        id (int): Big serial primary key.
        time (datetime): Prediction timestamp (UTC).
        symbol_id (int): Foreign key to Symbol.
        model_name (str): Model identifier (tft, hmm_garch, gnn, lstm_attn, xgboost).
        horizon_days (int): Forecast horizon in days (1, 5, 21).
        p10_return (Decimal): 10th percentile predicted return.
        p50_return (Decimal): Median (50th percentile) predicted return.
        p90_return (Decimal): 90th percentile predicted return.
        raw_signal (Decimal): Continuous signal in range [-1, +1].
        confidence (Decimal): Model agreement score in range [0, 1].
        shap_values (dict): Per-feature SHAP attribution values.
        attention_weights (dict): Attention weight array (for TFT, LSTM-Attn).
        actual_return (Decimal): Realized return (filled retrospectively).
        created_at (datetime): Prediction creation timestamp (UTC).
    
    Indexes:
        - (symbol_id, time DESC, model_name) for fast prediction lookup
    """

    __tablename__ = "ml_predictions"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        doc="Big serial primary key",
    )
    time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Prediction timestamp (UTC)",
    )
    symbol_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("symbols.id"),
        nullable=False,
        index=True,
        doc="Foreign key to symbols",
    )
    model_name: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="Model identifier (tft, hmm_garch, gnn, lstm_attn, xgboost)",
    )
    horizon_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Forecast horizon in days",
    )
    p10_return: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
        doc="10th percentile predicted return",
    )
    p50_return: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
        doc="Median (50th percentile) predicted return",
    )
    p90_return: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
        doc="90th percentile predicted return",
    )
    raw_signal: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 4),
        nullable=True,
        doc="Continuous signal in range [-1, +1]",
    )
    confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        doc="Model confidence/agreement score [0, 1]",
    )
    shap_values: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Per-feature SHAP attribution values",
    )
    attention_weights: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Attention weight arrays (TFT, LSTM-Attn)",
    )
    actual_return: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        nullable=True,
        doc="Realized return (filled retrospectively)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Prediction creation timestamp (UTC)",
    )

    def __repr__(self) -> str:
        return f"<MLPrediction(symbol_id={self.symbol_id}, model='{self.model_name}', horizon={self.horizon_days}d)>"
