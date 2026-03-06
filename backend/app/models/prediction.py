"""ML prediction model storing forecast results from all models."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="tft | cnn_bilstm | xgboost_lgbm | hmm | finbert",
    )
    forecast_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Date when the prediction was made",
    )
    target_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Date being predicted (1d, 5d, 30d ahead)",
    )
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, comment="1, 5, or 30")
    predicted_price: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_direction: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="up | down | neutral"
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Model confidence score 0-100"
    )
    prediction_low: Mapped[float | None] = mapped_column(Float, nullable=True, comment="Lower CI bound")
    prediction_high: Mapped[float | None] = mapped_column(Float, nullable=True, comment="Upper CI bound")
    actual_price: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Filled in after target date passes"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return (
            f"<Prediction(symbol='{self.symbol}', model='{self.model_name}', "
            f"target='{self.target_date}', price={self.predicted_price})>"
        )
