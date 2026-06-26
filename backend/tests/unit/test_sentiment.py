from __future__ import annotations

from unittest.mock import MagicMock, patch
from app.services.sentiment_analyzer import FinBERTSentimentAnalyzer

def test_sentiment_analyzer_fallback() -> None:
    analyzer = FinBERTSentimentAnalyzer()
    with patch.object(analyzer, "initialize") as mock_init:
        analyzer._initialized = False
        res = analyzer.analyze_sentiment("TCS shares rise on strong earnings.")
        assert res == {"positive": 0.0, "negative": 0.0, "neutral": 1.0}

def test_get_stock_sentiment_with_mocked_headlines() -> None:
    analyzer = FinBERTSentimentAnalyzer()
    
    mock_headlines = [
        {"text": "RELIANCE Q3 results beat estimates, stock gains", "date": "2026-06-25"},
        {"text": "Market opens flat today", "date": "2026-06-25"}
    ]
    
    with patch.object(analyzer, "analyze_sentiment") as mock_analyze:
        mock_analyze.return_value = {"positive": 0.8, "negative": 0.1, "neutral": 0.1}
        score = analyzer.get_stock_sentiment("RELIANCE.NS", mock_headlines)
        
        assert abs(score - 0.7) < 1e-5
