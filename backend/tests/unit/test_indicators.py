"""
Test indicators vs reference libraries (pandas-ta).
"""
import numpy as np
import pandas as pd
import pandas_ta as ta

from nqml.features.fs_v1 import atr_pct_14, rsi_14, supertrend


def _generate_test_bars(length=500):
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=length, freq="B")

    returns = np.random.normal(0, 0.01, size=length)
    price = 100 * np.exp(np.cumsum(returns))

    high = price * (1 + np.abs(np.random.normal(0, 0.005, size=length)))
    low = price * (1 - np.abs(np.random.normal(0, 0.005, size=length)))
    open_price = price * (1 + np.random.normal(0, 0.002, size=length))

    return pd.DataFrame({
        "open": open_price,
        "high": high,
        "low": low,
        "close": price,
        "volume": np.ones(length)
    }, index=dates)

def test_rsi_14_matches_pandas_ta():
    bars = _generate_test_bars()

    # Custom nqml RSI
    custom_rsi = rsi_14(bars)

    # pandas-ta RSI
    pta_rsi = ta.rsi(bars["close"], length=14)

    # Compare valid ranges (ignore first 14 NaN)
    valid_idx = ~custom_rsi.isna() & ~pta_rsi.isna()

    pd.testing.assert_series_equal(
        custom_rsi[valid_idx],
        pta_rsi[valid_idx],
        check_names=False,
        rtol=5e-2,
        atol=1e-3
    )

def test_atr_pct_14_matches_pandas_ta():
    bars = _generate_test_bars()

    # Custom nqml ATR%
    custom_atr_pct = atr_pct_14(bars)

    # pandas-ta ATR
    pta_atr = ta.atr(bars["high"], bars["low"], bars["close"], length=14)
    pta_atr_pct = pta_atr / bars["close"]

    valid_idx = ~custom_atr_pct.isna() & ~pta_atr_pct.isna()

    pd.testing.assert_series_equal(
        custom_atr_pct[valid_idx],
        pta_atr_pct[valid_idx],
        check_names=False,
        rtol=5e-2,
        atol=1e-3
    )

def test_supertrend_smoke():
    bars = _generate_test_bars()
    st = supertrend(bars)
    assert "supertrend_dir" in st.columns
    assert "supertrend_dist_pct" in st.columns
    # Ensure it's populated
    assert not st["supertrend_dir"].iloc[20:].isna().any()
