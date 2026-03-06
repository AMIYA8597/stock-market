"""News sentiment model for storing FinBERT-analyzed financial news."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NewsSentiment(Base):
    __tablename__ = "news_sentiment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sentiment_score: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Continuous sentiment score from -1.0 (bearish) to +1.0 (bullish)",
    )
    sentiment_label: Mapped[str] = mapped_column(
        String(10), nullable=False,
        comment="positive | negative | neutral",
    )
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return (
            f"<Sentiment(symbol='{self.symbol}', label='{self.sentiment_label}', "
            f"score={self.sentiment_score})>"
        )
