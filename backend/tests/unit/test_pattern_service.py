import pandas as pd

from app.services.pattern_service import detect_patterns


def test_detect_patterns_empty():
    df = pd.DataFrame()
    assert detect_patterns(df) == []


def test_detect_patterns_doji():
    df = pd.DataFrame(
        {"open": [100.0] * 10, "high": [105.0] * 10, "low": [95.0] * 10, "close": [100.0] * 10}
    )
    markers = detect_patterns(df)
    assert any("Doji" in m["text"] for m in markers)


def test_detect_patterns_engulfing():
    # Down-trend for 5 days, then bullish engulfing
    df = pd.DataFrame(
        {
            "open": [150.0, 140.0, 130.0, 120.0, 102.0, 98.0],
            "high": [151.0, 141.0, 131.0, 121.0, 103.0, 107.0],
            "low": [149.0, 139.0, 129.0, 119.0, 97.0, 97.0],
            "close": [145.0, 135.0, 125.0, 115.0, 99.0, 106.0],
        }
    )
    markers = detect_patterns(df)
    assert any("Bullish Engulfing" in m["text"] for m in markers)


def test_detect_patterns_three_white_soldiers():
    # Downtrend then 3 strong green candles
    df = pd.DataFrame(
        {
            "open": [150.0, 140.0, 130.0, 120.0, 100.0, 102.0, 104.0],
            "high": [151.0, 141.0, 131.0, 121.0, 103.0, 105.0, 107.0],
            "low": [149.0, 139.0, 129.0, 119.0, 99.0, 101.0, 103.0],
            "close": [145.0, 135.0, 125.0, 115.0, 102.0, 104.0, 106.0],
        }
    )
    markers = detect_patterns(df)
    assert any("Three White Soldiers" in m["text"] for m in markers)
