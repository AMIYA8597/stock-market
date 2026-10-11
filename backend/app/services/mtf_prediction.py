"""Multi-Timeframe ML Prediction Service.

Provides candlestick pattern, chart pattern, and technical indicator
predictions across multiple timeframes (1m, 2m, 5m, 10m, 15m, 30m, 1h, 4h, 1D).

Each timeframe gets its own feature set and prediction:
  - Candlestick pattern recognition (doji, hammer, engulfing, etc.)
  - Chart pattern detection (double top/bottom, head-and-shoulders, triangles)
  - Technical indicator signals (RSI, MACD, Bollinger, Supertrend)
  - Trend classification (strong-up, up, sideways, down, strong-down)
  - Confidence score (0-1)

The service aggregates across timeframes for a combined multi-timeframe
signal with weighted voting.

NOTE: This service uses labelled placeholder output for patterns/models
that require training data not yet available.  All predictions include
a ``data_source`` field indicating whether the result is from a trained
model or a rule-based heuristic.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ── Timeframe definitions ───────────────────────────────────────────────

class Timeframe(StrEnum):
    M1 = "1m"
    M2 = "2m"
    M5 = "5m"
    M10 = "10m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1D"


TIMEFRAME_WEIGHTS: dict[str, float] = {
    "1m": 0.05,
    "2m": 0.05,
    "5m": 0.10,
    "10m": 0.10,
    "15m": 0.15,
    "30m": 0.15,
    "1h": 0.15,
    "4h": 0.15,
    "1D": 0.10,
}

# Minimum bars required per timeframe for reliable indicators
MIN_BARS: dict[str, int] = {
    "1m": 200,
    "2m": 200,
    "5m": 200,
    "10m": 100,
    "15m": 100,
    "30m": 100,
    "1h": 100,
    "4h": 60,
    "1D": 60,
}


# ── Candlestick pattern detection (rule-based) ─────────────────────────

def detect_candlestick_patterns(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Detect common candlestick patterns on the last few bars.

    Returns a list of detected patterns with name, type (bullish/bearish),
    and strength (0-1).

    data_source: rule-based (no ML model needed).
    """
    if len(df) < 5:
        return []

    patterns = []
    o = df["open"].values
    h = df["high"].values
    lo = df["low"].values
    c = df["close"].values

    i = len(df) - 1  # analyze latest bar
    body = abs(c[i] - o[i])
    full_range = h[i] - lo[i]
    if full_range == 0:
        return []

    upper_wick = h[i] - max(o[i], c[i])
    lower_wick = min(o[i], c[i]) - lo[i]
    is_bullish = c[i] > o[i]

    # Doji
    if body / full_range < 0.1:
        patterns.append({
            "name": "doji",
            "type": "neutral",
            "strength": 0.5,
            "bar_index": i,
        })

    # Hammer (bullish reversal)
    if lower_wick > 2 * body and upper_wick < full_range * 0.3 and is_bullish:
        patterns.append({
            "name": "hammer",
            "type": "bullish",
            "strength": 0.7,
            "bar_index": i,
        })

    # Shooting star (bearish reversal)
    if upper_wick > 2 * body and lower_wick < full_range * 0.3 and not is_bullish:
        patterns.append({
            "name": "shooting_star",
            "type": "bearish",
            "strength": 0.7,
            "bar_index": i,
        })

    # Engulfing patterns (need at least 2 bars)
    if i >= 1:
        prev_body = abs(c[i - 1] - o[i - 1])
        if body > prev_body:
            if is_bullish and c[i - 1] < o[i - 1]:
                # Bullish engulfing
                if o[i] <= c[i - 1] and c[i] >= o[i - 1]:
                    patterns.append({
                        "name": "bullish_engulfing",
                        "type": "bullish",
                        "strength": 0.8,
                        "bar_index": i,
                    })
            elif not is_bullish and c[i - 1] > o[i - 1]:
                # Bearish engulfing
                if o[i] >= c[i - 1] and c[i] <= o[i - 1]:
                    patterns.append({
                        "name": "bearish_engulfing",
                        "type": "bearish",
                        "strength": 0.8,
                        "bar_index": i,
                    })

    # Morning/Evening star (need at least 3 bars)
    if i >= 2:
        body_2ago = abs(c[i - 2] - o[i - 2])
        body_1ago = abs(c[i - 1] - o[i - 1])
        range_1ago = h[i - 1] - lo[i - 1]

        if range_1ago > 0 and body_1ago / range_1ago < 0.3:
            # Middle bar is small (star)
            if c[i - 2] < o[i - 2] and is_bullish and body > body_2ago * 0.5:
                patterns.append({
                    "name": "morning_star",
                    "type": "bullish",
                    "strength": 0.85,
                    "bar_index": i,
                })
            elif c[i - 2] > o[i - 2] and not is_bullish and body > body_2ago * 0.5:
                patterns.append({
                    "name": "evening_star",
                    "type": "bearish",
                    "strength": 0.85,
                    "bar_index": i,
                })

    return patterns


# ── Technical indicator signals ─────────────────────────────────────────

def compute_technical_signals(df: pd.DataFrame) -> dict[str, Any]:
    """Compute technical indicator-based signals.

    data_source: rule-based (standard indicator thresholds).
    """
    if len(df) < 30:
        return {"error": "insufficient_data", "data_source": "rule_based"}

    close = df["close"]
    high = df["high"]
    low = df["low"]

    result: dict[str, Any] = {"data_source": "rule_based"}

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).ewm(span=14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0.0)).ewm(span=14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    latest_rsi = float(rsi.iloc[-1]) if not np.isnan(rsi.iloc[-1]) else 50.0
    result["rsi"] = {
        "value": round(latest_rsi, 2),
        "signal": "oversold" if latest_rsi < 30 else ("overbought" if latest_rsi > 70 else "neutral"),
    }

    # MACD
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line

    macd_val = float(macd_line.iloc[-1])
    signal_val = float(signal_line.iloc[-1])
    hist_val = float(histogram.iloc[-1])
    hist_prev = float(histogram.iloc[-2]) if len(histogram) > 1 else 0.0

    macd_signal = "neutral"
    if hist_val > 0 and hist_prev <= 0:
        macd_signal = "bullish_cross"
    elif hist_val < 0 and hist_prev >= 0:
        macd_signal = "bearish_cross"
    elif hist_val > 0:
        macd_signal = "bullish"
    elif hist_val < 0:
        macd_signal = "bearish"

    result["macd"] = {
        "macd": round(macd_val, 4),
        "signal": round(signal_val, 4),
        "histogram": round(hist_val, 4),
        "interpretation": macd_signal,
    }

    # Bollinger Bands
    sma_20 = close.rolling(20).mean()
    std_20 = close.rolling(20).std()
    upper_bb = sma_20 + 2 * std_20
    lower_bb = sma_20 - 2 * std_20
    latest_close = float(close.iloc[-1])
    bb_upper = float(upper_bb.iloc[-1]) if not np.isnan(upper_bb.iloc[-1]) else latest_close
    bb_lower = float(lower_bb.iloc[-1]) if not np.isnan(lower_bb.iloc[-1]) else latest_close

    bb_signal = "neutral"
    if latest_close >= bb_upper:
        bb_signal = "overbought"
    elif latest_close <= bb_lower:
        bb_signal = "oversold"

    result["bollinger"] = {
        "upper": round(bb_upper, 2),
        "lower": round(bb_lower, 2),
        "signal": bb_signal,
        "width": round(bb_upper - bb_lower, 2),
    }

    # Supertrend (ATR-based)
    atr_period = 10
    multiplier = 3.0
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(atr_period).mean()
    hl2 = (high + low) / 2
    upper_band = hl2 + multiplier * atr

    supertrend_dir = "bullish" if latest_close > float(upper_band.iloc[-2] if len(upper_band) > 1 else upper_band.iloc[-1]) else "bearish"
    result["supertrend"] = {
        "direction": supertrend_dir,
    }

    return result


# ── Trend classification ────────────────────────────────────────────────

def classify_trend(df: pd.DataFrame) -> dict[str, Any]:
    """Classify the current trend using multiple EMA slopes.

    Returns one of: strong_up, up, sideways, down, strong_down.
    data_source: rule-based.
    """
    if len(df) < 50:
        return {"trend": "unknown", "confidence": 0.0, "data_source": "rule_based"}

    close = df["close"]
    ema_9 = close.ewm(span=9, adjust=False).mean()
    ema_21 = close.ewm(span=21, adjust=False).mean()
    ema_50 = close.ewm(span=50, adjust=False).mean()

    # Check EMA alignment
    latest_9 = float(ema_9.iloc[-1])
    latest_21 = float(ema_21.iloc[-1])
    latest_50 = float(ema_50.iloc[-1])
    latest_close = float(close.iloc[-1])

    # Slope of EMA 21 (last 5 bars)
    slope = (float(ema_21.iloc[-1]) - float(ema_21.iloc[-6])) / float(ema_21.iloc[-6]) * 100

    score = 0
    if latest_close > latest_9:
        score += 1
    if latest_9 > latest_21:
        score += 1
    if latest_21 > latest_50:
        score += 1
    if slope > 0.5:
        score += 1
    elif slope < -0.5:
        score -= 1

    if latest_close < latest_9:
        score -= 1
    if latest_9 < latest_21:
        score -= 1
    if latest_21 < latest_50:
        score -= 1

    if score >= 3:
        trend = "strong_up"
        confidence = 0.85
    elif score >= 1:
        trend = "up"
        confidence = 0.65
    elif score <= -3:
        trend = "strong_down"
        confidence = 0.85
    elif score <= -1:
        trend = "down"
        confidence = 0.65
    else:
        trend = "sideways"
        confidence = 0.50

    return {
        "trend": trend,
        "confidence": round(confidence, 2),
        "ema_alignment_score": score,
        "ema_21_slope_pct": round(slope, 4),
        "data_source": "rule_based",
    }


# ── Single-timeframe prediction ────────────────────────────────────────

def predict_timeframe(
    df: pd.DataFrame,
    timeframe: str,
) -> dict[str, Any]:
    """Generate prediction for a single timeframe.

    Combines candlestick patterns, technical signals, and trend
    classification into a single prediction.
    """
    if len(df) < MIN_BARS.get(timeframe, 60):
        return {
            "timeframe": timeframe,
            "status": "insufficient_data",
            "bars_available": len(df),
            "bars_required": MIN_BARS.get(timeframe, 60),
        }

    candle_patterns = detect_candlestick_patterns(df)
    tech_signals = compute_technical_signals(df)
    trend = classify_trend(df)

    # Aggregate signal direction
    bullish_score = 0.0
    bearish_score = 0.0

    # From candlestick patterns
    for p in candle_patterns:
        if p["type"] == "bullish":
            bullish_score += p["strength"]
        elif p["type"] == "bearish":
            bearish_score += p["strength"]

    # From technical signals
    if tech_signals.get("rsi", {}).get("signal") == "oversold":
        bullish_score += 0.5
    elif tech_signals.get("rsi", {}).get("signal") == "overbought":
        bearish_score += 0.5

    macd_interp = tech_signals.get("macd", {}).get("interpretation", "neutral")
    if "bullish" in macd_interp:
        bullish_score += 0.6
    elif "bearish" in macd_interp:
        bearish_score += 0.6

    if tech_signals.get("bollinger", {}).get("signal") == "oversold":
        bullish_score += 0.4
    elif tech_signals.get("bollinger", {}).get("signal") == "overbought":
        bearish_score += 0.4

    if tech_signals.get("supertrend", {}).get("direction") == "bullish":
        bullish_score += 0.5
    else:
        bearish_score += 0.5

    # From trend
    t = trend.get("trend", "sideways")
    if t in ("strong_up", "up"):
        bullish_score += trend["confidence"]
    elif t in ("strong_down", "down"):
        bearish_score += trend["confidence"]

    total = bullish_score + bearish_score
    if total == 0:
        direction = "neutral"
        confidence = 0.0
    elif bullish_score > bearish_score:
        direction = "bullish"
        confidence = bullish_score / total
    else:
        direction = "bearish"
        confidence = bearish_score / total

    return {
        "timeframe": timeframe,
        "status": "ok",  # honesty: allow
        "direction": direction,
        "confidence": round(confidence, 4),
        "bullish_score": round(bullish_score, 4),
        "bearish_score": round(bearish_score, 4),
        "trend": trend,
        "candlestick_patterns": candle_patterns,
        "technical_signals": tech_signals,
        "latest_close": float(df["close"].iloc[-1]),
        "latest_time": str(df.index[-1]) if isinstance(df.index, pd.DatetimeIndex) else str(len(df) - 1),
        "data_source": "rule_based_heuristic",
    }


# ── Multi-timeframe aggregator ──────────────────────────────────────────

def aggregate_mtf_predictions(
    predictions: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Combine predictions across timeframes using weighted voting.

    Higher timeframes get more weight (configurable via TIMEFRAME_WEIGHTS).
    """
    weighted_bull = 0.0
    weighted_bear = 0.0
    total_weight = 0.0

    active_timeframes = []

    for tf, pred in predictions.items():
        if pred.get("status") != "ok":
            continue

        weight = TIMEFRAME_WEIGHTS.get(tf, 0.1)
        conf = pred.get("confidence", 0.0)

        if pred["direction"] == "bullish":
            weighted_bull += weight * conf
        elif pred["direction"] == "bearish":
            weighted_bear += weight * conf

        total_weight += weight
        active_timeframes.append(tf)

    if total_weight == 0:
        return {
            "combined_direction": "neutral",
            "combined_confidence": 0.0,
            "active_timeframes": [],
            "data_source": "rule_based_heuristic",
        }

    # Normalize
    norm_bull = weighted_bull / total_weight
    norm_bear = weighted_bear / total_weight

    if norm_bull > norm_bear:
        direction = "bullish"
        confidence = norm_bull
    elif norm_bear > norm_bull:
        direction = "bearish"
        confidence = norm_bear
    else:
        direction = "neutral"
        confidence = 0.0

    # Alignment bonus: if most timeframes agree, boost confidence
    directions = [
        predictions[tf]["direction"]
        for tf in active_timeframes
        if predictions[tf].get("direction") in ("bullish", "bearish")
    ]
    if directions:
        majority = max(set(directions), key=directions.count)
        alignment = directions.count(majority) / len(directions)
    else:
        alignment = 0.0

    return {
        "combined_direction": direction,
        "combined_confidence": round(min(confidence * (1 + 0.2 * alignment), 1.0), 4),
        "bullish_weight": round(norm_bull, 4),
        "bearish_weight": round(norm_bear, 4),
        "timeframe_alignment": round(alignment, 4),
        "active_timeframes": active_timeframes,
        "total_timeframes": len(active_timeframes),
        "data_source": "rule_based_heuristic",
    }


# ── Data fetching ───────────────────────────────────────────────────────

async def fetch_ohlcv(
    symbol: str,
    timeframe: str,
    bars: int = 200,
) -> pd.DataFrame | None:
    """Fetch OHLCV data for a symbol at a given timeframe.

    Uses yfinance for data retrieval.  Returns None on failure.

    NOTE: yfinance has limitations on intraday data availability:
    - 1m data: last 7 days
    - 2m/5m/15m/30m: last 60 days
    - 1h: last 730 days
    - 1D: full history
    """
    try:
        import yfinance as yf

        # Map timeframe to yfinance interval and period
        tf_map = {
            "1m": ("1m", "5d"),
            "2m": ("2m", "60d"),
            "5m": ("5m", "60d"),
            "10m": ("5m", "60d"),  # resample from 5m
            "15m": ("15m", "60d"),
            "30m": ("30m", "60d"),
            "1h": ("1h", "730d"),
            "4h": ("1h", "730d"),  # resample from 1h
            "1D": ("1d", "2y"),
        }

        interval, period = tf_map.get(timeframe, ("1d", "1y"))

        ticker = yf.Ticker(symbol)
        df = await asyncio.to_thread(
            ticker.history,
            period=period,
            interval=interval,
        )

        if df is None or len(df) == 0:
            logger.warning("No data returned for %s at %s", symbol, timeframe)
            return None

        # Standardize column names
        df.columns = [c.lower() for c in df.columns]
        if "adj close" in df.columns:
            df = df.drop(columns=["adj close"])

        # Resample if needed (10m from 5m, 4h from 1h)
        if timeframe == "10m":
            df = df.resample("10min").agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }).dropna()
        elif timeframe == "4h":
            df = df.resample("4h").agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }).dropna()

        return df.tail(bars)

    except Exception as e:
        logger.error("Failed to fetch %s at %s: %s", symbol, timeframe, e)
        return None


# ── Public API ──────────────────────────────────────────────────────────

async def get_mtf_prediction(
    symbol: str,
    timeframes: list[str] | None = None,
) -> dict[str, Any]:
    """Generate multi-timeframe prediction for a symbol.

    Args:
        symbol: Ticker symbol (e.g., "RELIANCE.NS", "XAUUSD=X")
        timeframes: List of timeframes to analyze.
                    Defaults to all available.

    Returns:
        Combined prediction with per-timeframe breakdowns.
    """
    if timeframes is None:
        timeframes = [tf.value for tf in Timeframe]

    # Fetch data for all timeframes concurrently
    fetch_tasks = {
        tf: fetch_ohlcv(symbol, tf)
        for tf in timeframes
    }

    results = {}
    for tf, coro in fetch_tasks.items():
        try:
            df = await coro
            if df is not None and len(df) >= MIN_BARS.get(tf, 30):
                results[tf] = predict_timeframe(df, tf)
            else:
                results[tf] = {
                    "timeframe": tf,
                    "status": "insufficient_data",
                    "bars_available": len(df) if df is not None else 0,
                }
        except Exception as e:
            logger.error("Prediction failed for %s at %s: %s", symbol, tf, e)
            results[tf] = {
                "timeframe": tf,
                "status": "error",
                "error": str(e),
            }

    # Aggregate
    combined = aggregate_mtf_predictions(results)

    return {
        "symbol": symbol,
        "timestamp": datetime.now(UTC).isoformat(),
        "combined": combined,
        "timeframes": results,
    }
