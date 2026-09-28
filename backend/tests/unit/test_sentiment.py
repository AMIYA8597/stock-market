from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.sentiment_analyzer import FinBERTSentimentAnalyzer

_FAKE_RSS = b"""<?xml version="1.0"?>
<rss><channel>
<item><title>RELIANCE hits 52-week high - Example News</title>
<pubDate>Mon, 01 Jan 2026 09:00:00 GMT</pubDate>
<link>https://news.google.com/rss/articles/fake</link></item>
</channel></rss>"""


def test_sentiment_analyzer_unavailable_raises() -> None:
    """When the model is not initialized and initialize() cannot load it
    (e.g. no-op mock, or FinBERT missing), analyze_sentiment must fail
    loudly rather than return a fabricated neutral-leaning score. A missing
    model means sentiment is genuinely unavailable, not "90% neutral".

    initialize() is mocked to fail rather than relying on FinBERT actually
    being unreachable: whether the real ProsusAI/finbert download succeeds
    depends on the runtime's network access, which is not something this
    test should be sensitive to. What must hold regardless of environment
    is that analyze_sentiment_batch propagates initialize()'s failure
    instead of swallowing it into a fallback score.
    """
    analyzer = FinBERTSentimentAnalyzer()
    analyzer._initialized = False
    with patch.object(
        analyzer, "initialize", side_effect=RuntimeError("FinBERT unavailable")
    ):
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


def test_scrape_google_news_caches_within_ttl() -> None:
    """Regression test: scrape_google_news() used to hit the live Google
    News RSS endpoint on every call with no caching at all, meaning every
    prediction request for a symbol re-scraped it synchronously. A second
    call for the same query within the TTL window must be served from
    cache, not trigger a second network request."""
    analyzer = FinBERTSentimentAnalyzer()
    analyzer._news_cache.clear()  # isolate from any other test/process state

    mock_response = MagicMock()
    mock_response.read.return_value = _FAKE_RSS
    mock_response.__enter__.return_value = mock_response
    mock_response.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        first = analyzer.scrape_google_news("RELIANCE stock India")
        second = analyzer.scrape_google_news("RELIANCE stock India")

        assert mock_urlopen.call_count == 1
        assert first == second
        assert len(first) == 1
        assert first[0]["text"] == "RELIANCE hits 52-week high"


def test_scrape_google_news_does_not_cache_failures() -> None:
    """A failed scrape (network error, timeout, ...) must not be cached -
    otherwise every call for the next 15 minutes would keep returning an
    empty result even after the underlying issue clears."""
    analyzer = FinBERTSentimentAnalyzer()
    analyzer._news_cache.clear()

    with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
        result = analyzer.scrape_google_news("a query that always fails")

    assert result == []
    assert "a query that always fails" not in analyzer._news_cache
