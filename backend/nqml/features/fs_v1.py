"""
Feature Set V1 (fs_v1) - Stationary and scale-free features
"""

import numpy as np
import pandas as pd

from nqml.features.registry import feature

# Note: Many of these rely on pandas/numpy operations.
# Missing ones will be handled gracefully.

@feature("log_ret_1", "return", {"periods": 1}, 2, "float32")
def log_ret_1(bars: pd.DataFrame) -> pd.Series:
    return np.log(bars["close"] / bars["close"].shift(1))

@feature("log_ret_2", "return", {"periods": 2}, 3, "float32")
def log_ret_2(bars: pd.DataFrame) -> pd.Series:
    return np.log(bars["close"] / bars["close"].shift(2))

@feature("log_ret_3", "return", {"periods": 3}, 4, "float32")
def log_ret_3(bars: pd.DataFrame) -> pd.Series:
    return np.log(bars["close"] / bars["close"].shift(3))

@feature("log_ret_5", "return", {"periods": 5}, 6, "float32")
def log_ret_5(bars: pd.DataFrame) -> pd.Series:
    return np.log(bars["close"] / bars["close"].shift(5))

@feature("log_ret_10", "return", {"periods": 10}, 11, "float32")
def log_ret_10(bars: pd.DataFrame) -> pd.Series:
    return np.log(bars["close"] / bars["close"].shift(10))

@feature("log_ret_21", "return", {"periods": 21}, 22, "float32")
def log_ret_21(bars: pd.DataFrame) -> pd.Series:
    return np.log(bars["close"] / bars["close"].shift(21))

@feature("overnight_gap", "return", {}, 2, "float32")
def overnight_gap(bars: pd.DataFrame) -> pd.Series:
    return np.log(bars["open"] / bars["close"].shift(1))

@feature("intraday_ret", "return", {}, 1, "float32")
def intraday_ret(bars: pd.DataFrame) -> pd.Series:
    return np.log(bars["close"] / bars["open"])

# Realized volatility (rolling std of log returns)
def _realized_vol(bars: pd.DataFrame, window: int) -> pd.Series:
    log_ret = np.log(bars["close"] / bars["close"].shift(1))
    return log_ret.rolling(window=window, min_periods=window).std(ddof=1) * np.sqrt(252)

@feature("realized_vol_5", "volatility", {"window": 5}, 6, "float32")
def realized_vol_5(bars: pd.DataFrame) -> pd.Series:
    return _realized_vol(bars, 5)

@feature("realized_vol_21", "volatility", {"window": 21}, 22, "float32")
def realized_vol_21(bars: pd.DataFrame) -> pd.Series:
    return _realized_vol(bars, 21)

@feature("realized_vol_63", "volatility", {"window": 63}, 64, "float32")
def realized_vol_63(bars: pd.DataFrame) -> pd.Series:
    return _realized_vol(bars, 63)

@feature("parkinson_vol_21", "volatility", {"window": 21}, 21, "float32")
def parkinson_vol_21(bars: pd.DataFrame) -> pd.Series:
    hl = np.log(bars["high"] / bars["low"]) ** 2
    # factor = 1 / (4 * ln(2)) ~= 0.36067
    factor = 1.0 / (4.0 * np.log(2.0))
    vol = (hl * factor).rolling(window=21, min_periods=21).mean()
    return np.sqrt(vol * 252)

@feature("garman_klass_vol_21", "volatility", {"window": 21}, 21, "float32")
def garman_klass_vol_21(bars: pd.DataFrame) -> pd.Series:
    log_hl = np.log(bars["high"] / bars["low"]) ** 2
    log_co = np.log(bars["close"] / bars["open"]) ** 2
    vol = (0.5 * log_hl - (2 * np.log(2) - 1) * log_co).rolling(window=21, min_periods=21).mean()
    return np.sqrt(vol * 252)

@feature("yang_zhang_vol_21", "volatility", {"window": 21}, 22, "float32")
def yang_zhang_vol_21(bars: pd.DataFrame) -> pd.Series:
    window = 21
    log_ho = np.log(bars["high"] / bars["open"])
    log_lo = np.log(bars["low"] / bars["open"])
    log_co = np.log(bars["close"] / bars["open"])

    log_oc = np.log(bars["open"] / bars["close"].shift(1))

    rs = log_ho * (log_ho - log_co) + log_lo * (log_lo - log_co)

    sigma_o_sq = log_oc.rolling(window=window).var(ddof=1)
    sigma_c_sq = log_co.rolling(window=window).var(ddof=1)
    sigma_rs_sq = rs.rolling(window=window).mean()

    k = 0.34 / (1.34 + (window + 1) / (window - 1))
    var = sigma_o_sq + k * sigma_c_sq + (1 - k) * sigma_rs_sq
    return np.sqrt(var * 252)

@feature("atr_pct_14", "volatility", {"window": 14}, 15, "float32")
def atr_pct_14(bars: pd.DataFrame) -> pd.Series:
    prev_close = bars["close"].shift(1)
    tr1 = bars["high"] - bars["low"]
    tr2 = (bars["high"] - prev_close).abs()
    tr3 = (bars["low"] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Wilder's smoothing
    atr = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    return atr / bars["close"]

@feature("price_sma_20_pct", "trend", {"window": 20}, 20, "float32")
def price_sma_20_pct(bars: pd.DataFrame) -> pd.Series:
    sma = bars["close"].rolling(window=20).mean()
    return bars["close"] / sma - 1.0

@feature("price_sma_50_pct", "trend", {"window": 50}, 50, "float32")
def price_sma_50_pct(bars: pd.DataFrame) -> pd.Series:
    sma = bars["close"].rolling(window=50).mean()
    return bars["close"] / sma - 1.0

@feature("price_sma_200_pct", "trend", {"window": 200}, 200, "float32")
def price_sma_200_pct(bars: pd.DataFrame) -> pd.Series:
    sma = bars["close"].rolling(window=200).mean()
    return bars["close"] / sma - 1.0

@feature("ema_spread_pct", "trend", {"fast": 12, "slow": 26}, 26, "float32")
def ema_spread_pct(bars: pd.DataFrame) -> pd.Series:
    ema_fast = bars["close"].ewm(span=12, adjust=False).mean()
    ema_slow = bars["close"].ewm(span=26, adjust=False).mean()
    return (ema_fast - ema_slow) / ema_slow

@feature("macd_hist_pct", "trend", {"fast": 12, "slow": 26, "signal": 9}, 35, "float32")
def macd_hist_pct(bars: pd.DataFrame) -> pd.Series:
    ema_fast = bars["close"].ewm(span=12, adjust=False).mean()
    ema_slow = bars["close"].ewm(span=26, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return hist / bars["close"]

@feature("adx_14", "trend", {"window": 14}, 28, "float32")
def adx_14(bars: pd.DataFrame) -> pd.DataFrame:
    up = bars["high"] - bars["high"].shift(1)
    down = bars["low"].shift(1) - bars["low"]

    pos_dm = np.where((up > down) & (up > 0), up, 0.0)
    neg_dm = np.where((down > up) & (down > 0), down, 0.0)

    pos_dm = pd.Series(pos_dm, index=bars.index)
    neg_dm = pd.Series(neg_dm, index=bars.index)

    prev_close = bars["close"].shift(1)
    tr1 = bars["high"] - bars["low"]
    tr2 = (bars["high"] - prev_close).abs()
    tr3 = (bars["low"] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Wilder's smoothing
    atr = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    pos_di = 100 * pos_dm.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr
    neg_di = 100 * neg_dm.ewm(alpha=1/14, min_periods=14, adjust=False).mean() / atr

    dx = 100 * (pos_di - neg_di).abs() / (pos_di + neg_di).replace(0, np.nan)
    adx = dx.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

    return pd.DataFrame({"adx_14": adx, "plus_di_14": pos_di, "minus_di_14": neg_di})

@feature("supertrend", "trend", {"window": 10, "multiplier": 3.0}, 11, "float32")
def supertrend(bars: pd.DataFrame) -> pd.DataFrame:
    # Basic Supertrend implementation
    prev_close = bars["close"].shift(1)
    tr1 = bars["high"] - bars["low"]
    tr2 = (bars["high"] - prev_close).abs()
    tr3 = (bars["low"] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=10).mean()

    hl2 = (bars["high"] + bars["low"]) / 2
    basic_ub = hl2 + 3.0 * atr
    basic_lb = hl2 - 3.0 * atr

    # In a full implementation, we'd need a recursive loop for Supertrend bands.
    # We will approximate Supertrend using a simpler pandas-friendly method or iterate.
    # To keep it completely vectorized but accurate, it's tricky, but here is the loop:

    n = len(bars)
    ub = np.zeros(n)
    lb = np.zeros(n)
    st = np.zeros(n)
    dir_arr = np.ones(n)

    close = bars["close"].values
    basic_ub_v = basic_ub.values
    basic_lb_v = basic_lb.values

    for i in range(1, n):
        if np.isnan(basic_ub_v[i]):
            continue

        # UB
        if basic_ub_v[i] < ub[i-1] or close[i-1] > ub[i-1]:
            ub[i] = basic_ub_v[i]
        else:
            ub[i] = ub[i-1]

        # LB
        if basic_lb_v[i] > lb[i-1] or close[i-1] < lb[i-1]:
            lb[i] = basic_lb_v[i]
        else:
            lb[i] = lb[i-1]

        # Direction
        if st[i-1] == ub[i-1] and close[i] < ub[i]:
            dir_arr[i] = -1
            st[i] = ub[i]
        elif st[i-1] == ub[i-1] and close[i] >= ub[i]:
            dir_arr[i] = 1
            st[i] = lb[i]
        elif st[i-1] == lb[i-1] and close[i] > lb[i]:
            dir_arr[i] = 1
            st[i] = lb[i]
        elif st[i-1] == lb[i-1] and close[i] <= lb[i]:
            dir_arr[i] = -1
            st[i] = ub[i]
        else:
            # Initial state
            dir_arr[i] = 1
            st[i] = lb[i]

    # Set to NaN where ATR is NaN
    dir_arr[np.isnan(basic_ub_v)] = np.nan
    st[np.isnan(basic_ub_v)] = np.nan

    dist_pct = (close - st) / close
    return pd.DataFrame({
        "supertrend_dir": dir_arr,
        "supertrend_dist_pct": dist_pct
    }, index=bars.index)

@feature("rsi_14", "momentum", {"window": 14}, 15, "float32")
def rsi_14(bars: pd.DataFrame) -> pd.Series:
    delta = bars["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder's smoothing
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    # Handle division by zero
    rsi = rsi.fillna(100).where(avg_loss != 0, 100)
    rsi[avg_gain.isna() | avg_loss.isna()] = np.nan
    return rsi

@feature("stoch_k_d", "momentum", {"k": 14, "d": 3}, 16, "float32")
def stoch_k_d(bars: pd.DataFrame) -> pd.DataFrame:
    lowest_low = bars["low"].rolling(window=14).min()
    highest_high = bars["high"].rolling(window=14).max()

    k = 100 * (bars["close"] - lowest_low) / (highest_high - lowest_low)
    d = k.rolling(window=3).mean()

    return pd.DataFrame({"stoch_k": k, "stoch_d": d})

@feature("roc_10", "momentum", {"window": 10}, 11, "float32")
def roc_10(bars: pd.DataFrame) -> pd.Series:
    return (bars["close"] / bars["close"].shift(10) - 1.0) * 100

@feature("cci_20", "momentum", {"window": 20}, 20, "float32")
def cci_20(bars: pd.DataFrame) -> pd.Series:
    tp = (bars["high"] + bars["low"] + bars["close"]) / 3
    sma = tp.rolling(window=20).mean()
    # Mean Absolute Deviation
    mad = tp.rolling(window=20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    cci = (tp - sma) / (0.015 * mad)
    return cci

@feature("williams_r_14", "momentum", {"window": 14}, 14, "float32")
def williams_r_14(bars: pd.DataFrame) -> pd.Series:
    lowest_low = bars["low"].rolling(window=14).min()
    highest_high = bars["high"].rolling(window=14).max()
    return -100 * (highest_high - bars["close"]) / (highest_high - lowest_low)

@feature("mom_12_1", "momentum", {"window": 252, "skip": 21}, 252, "float32")
def mom_12_1(bars: pd.DataFrame) -> pd.Series:
    # 12-1 month momentum is typically returns over past 12 months skipping the most recent 1 month.
    # 252 days total, skip 21 days. So price(t-21) / price(t-252)
    return bars["close"].shift(21) / bars["close"].shift(252) - 1.0

@feature("vol_zscore_20", "volume", {"window": 20}, 20, "float32")
def vol_zscore_20(bars: pd.DataFrame) -> pd.Series:
    mean_vol = bars["volume"].rolling(window=20).mean()
    std_vol = bars["volume"].rolling(window=20).std(ddof=1)
    return (bars["volume"] - mean_vol) / std_vol

@feature("obv_zscore_63", "volume", {"window": 63}, 64, "float32")
def obv_zscore_63(bars: pd.DataFrame) -> pd.Series:
    sign = np.sign(bars["close"].diff()).fillna(0)
    signed_volume = sign * bars["volume"]
    rolling_obv = signed_volume.rolling(window=63, min_periods=63).sum()
    mean_obv = rolling_obv.rolling(window=63, min_periods=63).mean()
    std_obv = rolling_obv.rolling(window=63, min_periods=63).std(ddof=1)
    return (rolling_obv - mean_obv) / std_obv

@feature("mfi_14", "volume", {"window": 14}, 15, "float32")
def mfi_14(bars: pd.DataFrame) -> pd.Series:
    tp = (bars["high"] + bars["low"] + bars["close"]) / 3
    rmf = tp * bars["volume"]

    diff = tp.diff()
    pos_mf = np.where(diff > 0, rmf, 0.0)
    neg_mf = np.where(diff < 0, rmf, 0.0)

    pos_mf = pd.Series(pos_mf, index=bars.index)
    neg_mf = pd.Series(neg_mf, index=bars.index)

    pos_sum = pos_mf.rolling(window=14).sum()
    neg_sum = neg_mf.rolling(window=14).sum()

    mfr = pos_sum / neg_sum
    mfi = 100 - (100 / (1 + mfr))
    mfi = mfi.fillna(100).where(neg_sum != 0, 100)
    mfi[pos_sum.isna() | neg_sum.isna()] = np.nan
    return mfi

@feature("ad_slope", "volume", {"window": 14}, 15, "float32")
def ad_slope(bars: pd.DataFrame) -> pd.Series:
    mfm = ((bars["close"] - bars["low"]) - (bars["high"] - bars["close"])) / (bars["high"] - bars["low"])
    mfm = mfm.fillna(0)
    mfv = mfm * bars["volume"]
    ad_diff = mfv.rolling(14).sum()
    ad_abs_sum = mfv.abs().rolling(14).sum()
    return ad_diff / ad_abs_sum

@feature("amihud_21", "liquidity", {"window": 21}, 21, "float32")
def amihud_21(bars: pd.DataFrame) -> pd.Series:
    ret = (bars["close"].pct_change()).abs()
    dollar_vol = bars["close"] * bars["volume"]
    amihud = ret / dollar_vol
    # Multiply by 1e6 for scaling
    return (amihud * 1e6).rolling(window=21).mean()

@feature("dist_high_low_252", "price", {"window": 252}, 252, "float32")
def dist_high_low_252(bars: pd.DataFrame) -> pd.DataFrame:
    high_252 = bars["high"].rolling(window=252).max()
    low_252 = bars["low"].rolling(window=252).min()

    dist_high = bars["close"] / high_252 - 1.0
    dist_low = bars["close"] / low_252 - 1.0

    return pd.DataFrame({"dist_high_252": dist_high, "dist_low_252": dist_low})

@feature("rolling_dd_252", "risk", {"window": 252}, 252, "float32")
def rolling_dd_252(bars: pd.DataFrame) -> pd.Series:
    # Not cummax! It's rolling max
    rolling_max = bars["high"].rolling(window=252).max()
    return bars["close"] / rolling_max - 1.0

@feature("calendar_features", "calendar", {}, 0, "float32")
def calendar_features(bars: pd.DataFrame) -> pd.DataFrame:
    idx = bars.index
    # assuming index is datetime
    dow = idx.dayofweek
    month = idx.month

    # Approx expiry week (last week of month)
    days_in_month = idx.days_in_month
    days_to_month_end = days_in_month - idx.day
    expiry_week_flag = (days_to_month_end <= 7).astype(float)

    return pd.DataFrame({
        "dow": dow,
        "month": month,
        "expiry_week_flag": expiry_week_flag,
        "days_to_month_end": days_to_month_end
    }, index=idx)

# Note: cross-sectional ranks/z-scores, relative return vs NIFTY, corr_to_index_63d
# require multi-asset inputs or a reference index.
# In a single-asset build_features context, we need to pass the index or do it elsewhere.
# Assuming the registry takes a single bars DataFrame, these might be populated with zeros
# if index data is unavailable, or we skip them here and handle them in fusion/cross-sectional engine.
# For fs_v1 single-asset, we will add placeholders that expect index data to be merged in ars if present,
# otherwise return zeros to satisfy the contract.

@feature("relative_return_21d", "cross_sectional", {"window": 21}, 21, "float32")
def relative_return_21d(bars: pd.DataFrame) -> pd.Series:
    # The reference index is required for this feature.
    ret_21 = bars["close"] / bars["close"].shift(21) - 1.0
    if "nifty_close" in bars.columns:
        nifty_ret_21 = bars["nifty_close"] / bars["nifty_close"].shift(21) - 1.0
        return ret_21 - nifty_ret_21
    return pd.Series(np.nan, index=bars.index, dtype="float64")

@feature("corr_to_index_63d", "cross_sectional", {"window": 63}, 63, "float32")
def corr_to_index_63d(bars: pd.DataFrame) -> pd.Series:
    ret = bars["close"].pct_change()
    if "nifty_close" in bars.columns:
        nifty_ret = bars["nifty_close"].pct_change()
        return ret.rolling(63).corr(nifty_ret)
    return pd.Series(np.nan, index=bars.index, dtype="float64")

@feature("cross_sectional_rank_21d", "cross_sectional", {"window": 21}, 21, "float32")
def cross_sectional_rank_21d(bars: pd.DataFrame) -> pd.Series:
    # A single-symbol frame cannot provide a cross-sectional rank.
    return pd.Series(np.nan, index=bars.index, dtype="float64")
