from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.sentiment_analyzer import FinBERTSentimentAnalyzer


def test_sentiment_analyzer_unavailable_raises() -> None:
    """When the model is not initialized and initialize() cannot load it
    (e.g. no-op mock, or FinBERT missing), analyze_sentiment must fail
    loudly rather than return a fabricated neutral-leaning score. A missing
    model means sentiment is genuinely unavailable, not "90% neutral"."""
    analyzer = FinBERTSentimentAnalyzer()
    analyzer._initialized = False
    with pytest.raises(RuntimeError):
        analyzer.analyze_sentiment("TCS shares rise on strong earnings.")


def test_get_stock_sentiment_with_mocked_headlines() -> None:
    analyzer = FinBERTSentimentAnalyzer()

    mock_headlines = [
        {"text": "RELIANCE Q3 results beat estimates, stock gains", "date": "2026-06-25"},
        {"text": "Market opens flat today", "date": "2026-06-25"},
    ]

    with patch.object(analyzer, "analyze_sentiment_batch") as mock_analyze:
        mock_analyze.return_value = [{"positive": 0.8, "negative": 0.1, "neutral": 0.1}] * 2
        score = analyzer.get_stock_sentiment("RELIANCE.NS", mock_headlines)

        assert abs(score - 0.7) < 1e-5
