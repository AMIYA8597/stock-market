"""Unit tests for the multi-timeframe prediction service.

Tests the rule-based components that don't require live data or ML models:
  - Candlestick pattern detection
  - Technical signal computation
  - Trend classification
  - Single-timeframe prediction
  - Multi-timeframe aggregation
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.mtf_prediction import (
    Timeframe,
    aggregate_mtf_predictions,
    classify_trend,
    compute_technical_signals,
    detect_candlestick_patterns,
    predict_timeframe,
)

# ── Helpers ──────────────────────────────────────────────────────────────


def _make_ohlcv(n: int = 100, trend: str = "up") -> pd.DataFrame:
    rng = np.random.default_rng(42)
    if trend == "up":
        close = np.linspace(100, 130, n) + rng.normal(0, 1, n)
    elif trend == "down":
        close = np.linspace(130, 100, n) + rng.normal(0, 1, n)
    else:
        close = np.full(n, 100.0) + rng.normal(0, 1, n)

    high = close + rng.uniform(0.5, 2, n)
    low = close - rng.uniform(0.5, 2, n)
    open_ = close + rng.normal(0, 0.5, n)
    volume = rng.integers(1000, 50000, n).astype(float)

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=pd.date_range("2024-01-01", periods=n, freq="h"),
    )


def _make_hammer_bar() -> pd.DataFrame:
    """Generate data ending with a hammer candle."""
    n = 10
    base = _make_ohlcv(n - 1, "down")
    # Append a hammer: small body at top, long lower wick
    hammer = pd.DataFrame({
        "open": [95.0],
        "high": [96.0],
        "low": [88.0],  # long lower wick
        "close": [95.5],  # bullish close
        "volume": [10000.0],
    }, index=[base.index[-1] + pd.Timedelta(hours=1)])
    return pd.concat([base, hammer])


def _make_engulfing() -> pd.DataFrame:
    """Generate data ending with a bullish engulfing."""
    n = 10
    base = _make_ohlcv(n - 2, "down")
    # Small bearish candle then large bullish engulfing
    bars = pd.DataFrame({
        "open": [95.0, 93.0],
        "high": [95.5, 97.0],
        "low": [93.5, 92.5],
        "close": [94.0, 96.0],
        "volume": [10000.0, 15000.0],
    }, index=pd.date_range(base.index[-1] + pd.Timedelta(hours=1), periods=2, freq="h"))
    return pd.concat([base, bars])


# ── Candlestick pattern tests ──────────────────────────────────────────


class TestCandlestickPatterns:
    def test_returns_list(self):
        df = _make_ohlcv(20)
        patterns = detect_candlestick_patterns(df)
        assert isinstance(patterns, list)

    def test_hammer_detection(self):
        df = _make_hammer_bar()
        patterns = detect_candlestick_patterns(df)
        names = [p["name"] for p in patterns]
        assert "hammer" in names
        hammer = next(p for p in patterns if p["name"] == "hammer")
        assert hammer["type"] == "bullish"
        assert 0 < hammer["strength"] <= 1

    def test_engulfing_detection(self):
        df = _make_engulfing()
        patterns = detect_candlestick_patterns(df)
        names = [p["name"] for p in patterns]
        assert "bullish_engulfing" in names

    def test_insufficient_data(self):
        df = _make_ohlcv(3)
        patterns = detect_candlestick_patterns(df)
        # Should not crash, may return empty or partial
        assert isinstance(patterns, list)

    def test_doji_detection(self):
        """A bar where open ≈ close should be detected as doji."""
        df = pd.DataFrame({
            "open": [100.0] * 5 + [100.0],
            "high": [101.0] * 5 + [102.0],
            "low": [99.0] * 5 + [98.0],
            "close": [100.0] * 5 + [100.01],  # tiny body
            "volume": [10000.0] * 6,
        })
        patterns = detect_candlestick_patterns(df)
        names = [p["name"] for p in patterns]
        assert "doji" in names


# ── Technical signals tests ─────────────────────────────────────────────


class TestTechnicalSignals:
    def test_returns_dict(self):
        df = _make_ohlcv(100)
        result = compute_technical_signals(df)
        assert isinstance(result, dict)
        assert "rsi" in result
        assert "macd" in result
        assert "bollinger" in result

    def test_rsi_range(self):
        df = _make_ohlcv(100)
        result = compute_technical_signals(df)
        rsi_val = result["rsi"]["value"]
        assert 0 <= rsi_val <= 100

    def test_insufficient_data(self):
        df = _make_ohlcv(10)
        result = compute_technical_signals(df)
        assert result.get("error") == "insufficient_data"

    def test_data_source_label(self):
        df = _make_ohlcv(100)
        result = compute_technical_signals(df)
        assert result["data_source"] == "rule_based"


# ── Trend classification tests ──────────────────────────────────────────


class TestTrendClassification:
    def test_uptrend(self):
        df = _make_ohlcv(100, "up")
        result = classify_trend(df)
        assert result["trend"] in ("strong_up", "up")
        assert result["confidence"] > 0.5

    def test_downtrend(self):
        df = _make_ohlcv(100, "down")
        result = classify_trend(df)
        assert result["trend"] in ("strong_down", "down")
        assert result["confidence"] > 0.5

    def test_data_source(self):
        df = _make_ohlcv(100)
        result = classify_trend(df)
        assert result["data_source"] == "rule_based"

    def test_insufficient_data(self):
        df = _make_ohlcv(20)
        result = classify_trend(df)
        assert result["trend"] == "unknown"


# ── Single-timeframe prediction tests ──────────────────────────────────


class TestPredictTimeframe:
    def test_ok_prediction(self):
        df = _make_ohlcv(200, "up")
        result = predict_timeframe(df, "1h")
        assert result["status"] == "ok"
        assert result["timeframe"] == "1h"
        assert result["direction"] in ("bullish", "bearish", "neutral")
        assert 0 <= result["confidence"] <= 1
        assert "candlestick_patterns" in result
        assert "technical_signals" in result
        assert "trend" in result

    def test_insufficient_data(self):
        df = _make_ohlcv(10)
        result = predict_timeframe(df, "1h")
        assert result["status"] == "insufficient_data"

    def test_data_source_labelled(self):
        df = _make_ohlcv(200)
        result = predict_timeframe(df, "15m")
        if result["status"] == "ok":
            assert result["data_source"] == "rule_based_heuristic"


# ── Multi-timeframe aggregation tests ──────────────────────────────────


class TestAggregation:
    def test_all_bullish(self):
        predictions = {
            "5m": {"status": "ok", "direction": "bullish", "confidence": 0.7},
            "15m": {"status": "ok", "direction": "bullish", "confidence": 0.8},
            "1h": {"status": "ok", "direction": "bullish", "confidence": 0.75},
        }
        result = aggregate_mtf_predictions(predictions)
        assert result["combined_direction"] == "bullish"
        assert result["combined_confidence"] > 0.5
        assert result["timeframe_alignment"] == 1.0

    def test_mixed_signals(self):
        predictions = {
            "5m": {"status": "ok", "direction": "bullish", "confidence": 0.8},
            "15m": {"status": "ok", "direction": "bearish", "confidence": 0.7},
            "1h": {"status": "ok", "direction": "bearish", "confidence": 0.9},
        }
        result = aggregate_mtf_predictions(predictions)
        assert result["combined_direction"] in ("bullish", "bearish")
        assert result["timeframe_alignment"] < 1.0

    def test_all_insufficient(self):
        predictions = {
            "1m": {"status": "insufficient_data"},
            "5m": {"status": "error"},
        }
        result = aggregate_mtf_predictions(predictions)
        assert result["combined_direction"] == "neutral"
        assert result["combined_confidence"] == 0.0
        assert result["active_timeframes"] == []

    def test_data_source_label(self):
        predictions = {
            "1h": {"status": "ok", "direction": "bullish", "confidence": 0.7},
        }
        result = aggregate_mtf_predictions(predictions)
        assert result["data_source"] == "rule_based_heuristic"

    def test_timeframe_enum(self):
        assert Timeframe.M1.value == "1m"
        assert Timeframe.D1.value == "1D"
        assert len(Timeframe) == 9
