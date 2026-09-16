"""Candlestick Pattern Service.

Ports the frontend patternDetector logic to the backend so that
charts, signals, and backtests all use identical logic.
"""

from __future__ import annotations

import pandas as pd


def detect_patterns(df: pd.DataFrame) -> list[dict]:
    """Detects classical candlestick patterns in an OHLCV DataFrame.

    Returns a list of markers formatted for Lightweight Charts and internal signalling.
    Marker format: {"time": int, "position": str, "shape": str, "color": str, "text": str}
    """
    markers = []

    if len(df) == 0:
        return markers

    # Pre-calculate standard series
    close = df["close"]
    open_ = df["open"]
    high = df["high"]
    low = df["low"]

    range_ = high - low
    body_size = (close - open_).abs()

    # Calculate upper and lower wicks securely
    max_oc = pd.concat([open_, close], axis=1).max(axis=1)
    min_oc = pd.concat([open_, close], axis=1).min(axis=1)

    upper_wick = high - max_oc
    lower_wick = min_oc - low

    is_bullish = close > open_

    # 5-bar SMA for trend
    sma5 = close.rolling(window=5, min_periods=1).mean()
    is_uptrend = close > sma5
    is_downtrend = close < sma5

    # We loop to generate markers (similar to frontend)
    for i in range(len(df)):
        if pd.isna(close.iloc[i]):
            continue

        rng = range_.iloc[i]
        if rng <= 0:
            continue

        bs = body_size.iloc[i]
        uw = upper_wick.iloc[i]
        lw = lower_wick.iloc[i]
        up_t = is_uptrend.iloc[i]
        dn_t = is_downtrend.iloc[i]
        bull = is_bullish.iloc[i]

        timestamp = (
            df.index[i].timestamp()
            if hasattr(df.index[i], "timestamp")
            else int(pd.to_datetime(df.index[i]).timestamp())
        )
        time_val = int(timestamp)

        # 1. Dragonfly Doji
        if bs <= rng * 0.05 and lw >= rng * 0.6 and uw <= rng * 0.1:
            markers.append(
                {
                    "time": time_val,
                    "position": "belowBar",
                    "shape": "arrowUp",
                    "color": "#FFEB3B",
                    "text": "Dragonfly Doji",
                }
            )
            continue

        # 2. Gravestone Doji
        if bs <= rng * 0.05 and uw >= rng * 0.6 and lw <= rng * 0.1:
            markers.append(
                {
                    "time": time_val,
                    "position": "aboveBar",
                    "shape": "arrowDown",
                    "color": "#FFC107",
                    "text": "Gravestone Doji",
                }
            )
            continue

        # 3. Doji
        if bs <= rng * 0.05:
            markers.append(
                {
                    "time": time_val,
                    "position": "inBar",
                    "shape": "circle",
                    "color": "#FFEB3B",
                    "text": "Doji",
                }
            )
            continue

        # 4. Marubozu
        if bs >= rng * 0.95:
            color = "#8E24AA" if bull else "#D81B60"
            markers.append(
                {
                    "time": time_val,
                    "position": "inBar",
                    "shape": "square",
                    "color": color,
                    "text": "Marubozu",
                }
            )
            continue

        # 5. Hammer
        if lw >= bs * 2 and uw <= rng * 0.1 and dn_t:
            markers.append(
                {
                    "time": time_val,
                    "position": "belowBar",
                    "shape": "arrowUp",
                    "color": "#00E676",
                    "text": "Hammer",
                }
            )
            continue

        # 6. Hanging Man
        if lw >= bs * 2 and uw <= rng * 0.1 and up_t:
            markers.append(
                {
                    "time": time_val,
                    "position": "aboveBar",
                    "shape": "arrowDown",
                    "color": "#FF3B5C",
                    "text": "Hanging Man",
                }
            )
            continue

        # 7. Inverted Hammer
        if uw >= bs * 2 and lw <= rng * 0.1 and dn_t:
            markers.append(
                {
                    "time": time_val,
                    "position": "belowBar",
                    "shape": "arrowUp",
                    "color": "#00E5FF",
                    "text": "Inv Hammer",
                }
            )
            continue

        # 8. Shooting Star
        if uw >= bs * 2 and lw <= rng * 0.1 and up_t:
            markers.append(
                {
                    "time": time_val,
                    "position": "aboveBar",
                    "shape": "arrowDown",
                    "color": "#E040FB",
                    "text": "Shooting Star",
                }
            )
            continue

        # 9. Spinning Top
        if bs > rng * 0.05 and bs <= rng * 0.3 and abs(uw - lw) <= rng * 0.2:
            markers.append(
                {
                    "time": time_val,
                    "position": "inBar",
                    "shape": "circle",
                    "color": "#3F51B5",
                    "text": "Spinning Top",
                }
            )
            continue

        # Multi-candle patterns
        if i >= 1:
            prev_bull = is_bullish.iloc[i - 1]
            prev_close = close.iloc[i - 1]
            prev_open = open_.iloc[i - 1]
            prev_bs = body_size.iloc[i - 1]
            curr_close = close.iloc[i]
            curr_open = open_.iloc[i]

            # Engulfing
            if (
                not prev_bull
                and bull
                and curr_close > prev_open
                and curr_open < prev_close
                and dn_t
            ):
                markers.append(
                    {
                        "time": time_val,
                        "position": "belowBar",
                        "shape": "arrowUp",
                        "color": "#00E676",
                        "text": "Bullish Engulfing",
                    }
                )
                continue
            if (
                prev_bull
                and not bull
                and curr_close < prev_open
                and curr_open > prev_close
                and up_t
            ):
                markers.append(
                    {
                        "time": time_val,
                        "position": "aboveBar",
                        "shape": "arrowDown",
                        "color": "#D81B60",
                        "text": "Bearish Engulfing",
                    }
                )
                continue

            # Harami
            if (
                not prev_bull
                and bull
                and curr_close < prev_open
                and curr_open > prev_close
                and prev_bs > bs * 2
                and dn_t
            ):
                markers.append(
                    {
                        "time": time_val,
                        "position": "belowBar",
                        "shape": "arrowUp",
                        "color": "#00E5FF",
                        "text": "Bullish Harami",
                    }
                )
                continue
            if (
                prev_bull
                and not bull
                and curr_close > prev_open
                and curr_open < prev_close
                and prev_bs > bs * 2
                and up_t
            ):
                markers.append(
                    {
                        "time": time_val,
                        "position": "aboveBar",
                        "shape": "arrowDown",
                        "color": "#FF3B5C",
                        "text": "Bearish Harami",
                    }
                )
                continue

        if i >= 2:
            p2_bull = is_bullish.iloc[i - 2]
            p2_close = close.iloc[i - 2]
            p2_open = open_.iloc[i - 2]
            p1_bull = is_bullish.iloc[i - 1]
            p1_bs = body_size.iloc[i - 1]
            p1_rng = range_.iloc[i - 1]
            curr_close = close.iloc[i]
            curr_open = open_.iloc[i]
            curr_bull = bull

            # Morning Star
            if (
                not p2_bull
                and p1_bs <= p1_rng * 0.1
                and curr_bull
                and curr_close > (p2_open + p2_close) / 2
                and dn_t
            ):
                markers.append(
                    {
                        "time": time_val,
                        "position": "belowBar",
                        "shape": "arrowUp",
                        "color": "#00E676",
                        "text": "Morning Star",
                    }
                )
                continue

            # Evening Star
            if (
                p2_bull
                and p1_bs <= p1_rng * 0.1
                and not curr_bull
                and curr_close < (p2_open + p2_close) / 2
                and up_t
            ):
                markers.append(
                    {
                        "time": time_val,
                        "position": "aboveBar",
                        "shape": "arrowDown",
                        "color": "#D81B60",
                        "text": "Evening Star",
                    }
                )
                continue

            # Three White Soldiers
            if (
                p2_bull
                and p1_bull
                and curr_bull
                and (curr_close > close.iloc[i - 1])
                and (close.iloc[i - 1] > close.iloc[i - 2])
                and dn_t
            ):
                markers.append(
                    {
                        "time": time_val,
                        "position": "belowBar",
                        "shape": "arrowUp",
                        "color": "#00E676",
                        "text": "Three White Soldiers",
                    }
                )
                continue

            # Three Black Crows
            if (
                not p2_bull
                and not p1_bull
                and not curr_bull
                and (curr_close < close.iloc[i - 1])
                and (close.iloc[i - 1] < close.iloc[i - 2])
                and up_t
            ):
                markers.append(
                    {
                        "time": time_val,
                        "position": "aboveBar",
                        "shape": "arrowDown",
                        "color": "#D81B60",
                        "text": "Three Black Crows",
                    }
                )
                continue

    return markers


def get_pattern_score(df: pd.DataFrame) -> dict:
    """Returns a scalar score and pattern summary for the latest bar."""
    markers = detect_patterns(df)
    if not markers:
        return {"pattern_score": 0.0, "patterns_detected": []}

    # Get markers for the latest bar
    latest_time = int(pd.to_datetime(df.index[-1]).timestamp())
    latest_markers = [m for m in markers if m["time"] == latest_time]

    score = 0.0
    names = []

    for m in latest_markers:
        txt = m["text"]
        names.append(txt)
        if m["shape"] == "arrowUp":
            score += 0.2
        elif m["shape"] == "arrowDown":
            score -= 0.2
        else:
            # Neutrals or continuations
            if txt == "Marubozu":
                score += 0.1 if m["color"] == "#8E24AA" else -0.1

    # Cap score
    score = max(-1.0, min(1.0, score))
    return {"pattern_score": score, "patterns_detected": names}
