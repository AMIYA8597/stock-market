"""News sentiment analysis results (FinBERT pipeline).

Financial news headlines analyzed with FinBERT transformer for sentiment scores.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class NewsSentiment(Base):
    """Financial news sentiment analysis.

    Fields:
        id (int): Big serial primary key.
        symbol_id (int): Foreign key to Symbol (nullable for market-wide news).
        headline (str): News headline text.
        source (str): News source (Reuters, Bloomberg, etc.).
        url (str): URL to full article.
        sentiment_label (str): Classification (POSITIVE, NEGATIVE, NEUTRAL).
        sentiment_score (Decimal): FinBERT probability score [0, 1].
        published_at (datetime): News publication timestamp (UTC).
        processed_at (datetime): When sentiment was analyzed (UTC).

    Indexes:
        - (symbol_id, published_at DESC) for time-series lookup
    """

    __tablename__ = "news_sentiment"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        doc="Big serial primary key",
    )
    symbol_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("symbols.id"),
        nullable=True,
        index=True,
        doc="Foreign key to symbols (nullable for market-wide news)",
    )
    headline: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="News headline text",
    )
    source: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        doc="News source (Reuters, Bloomberg, etc.)",
    )
    url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="URL to full article",
    )
    sentiment_label: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        doc="Classification (POSITIVE, NEGATIVE, NEUTRAL)",
    )
    sentiment_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        doc="FinBERT probability score [0, 1]",
    )
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="News publication timestamp (UTC)",
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When sentiment was analyzed (UTC)",
    )

    def __repr__(self) -> str:
        return f"<NewsSentiment(symbol_id={self.symbol_id}, label='{self.sentiment_label}', score={self.sentiment_score})>"
