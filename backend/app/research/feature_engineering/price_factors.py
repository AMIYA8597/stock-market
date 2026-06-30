import numpy as np
import pandas as pd
import pandas_ta as ta

class PriceFactorsBuilder:
    """Computes price-derived features and momentum factors."""

    def build(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df.copy()

        # Work on a copy sorted by index/time
        data = df.copy()
        if "time" in data.columns:
            data = data.sort_values("time")
        
        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        open_ = data["open"].astype(float)

        # 1. Log returns
        data["ret_1d"] = np.log(close / close.shift(1))
        data["ret_5d"] = np.log(close / close.shift(5))
        data["ret_21d"] = np.log(close / close.shift(21))
        data["ret_63d"] = np.log(close / close.shift(63))

        # 2. Momentum
        data["momentum_1d"] = close.pct_change(1)
        data["momentum_5d"] = close.pct_change(5)
        data["momentum_21d"] = close.pct_change(21)
        data["momentum_63d"] = close.pct_change(63)

        # 3. RSI
        rsi_series = ta.rsi(close, length=14)
        data["RSI_14"] = rsi_series if rsi_series is not None else 50.0

        # 4. MACD
        macd_df = ta.macd(close, fast=12, slow=26, signal=9)
        if macd_df is not None and not macd_df.empty:
            data["MACD_12_26_9"] = macd_df.iloc[:, 0]
            data["MACDh_12_26_9"] = macd_df.iloc[:, 1]
            data["MACDs_12_26_9"] = macd_df.iloc[:, 2]
        else:
            data["MACD_12_26_9"] = 0.0
            data["MACDh_12_26_9"] = 0.0
            data["MACDs_12_26_9"] = 0.0

        # 5. ADX
        adx_df = ta.adx(high, low, close, length=14)
        if adx_df is not None and not adx_df.empty:
            data["ADX_14"] = adx_df.iloc[:, 0]
            data["DMP_14"] = adx_df.iloc[:, 1]
            data["DMN_14"] = adx_df.iloc[:, 2]
        else:
            data["ADX_14"] = 20.0
            data["DMP_14"] = 20.0
            data["DMN_14"] = 20.0

        # 6. Candlestick Patterns (Pure Pandas Rules)
        body = (close - open_).abs()
        candle_range = high - low
        # Prevent division by zero
        candle_range = candle_range.replace(0, 1e-6)

        # Doji
        data["CDL_DOJI"] = (body <= 0.1 * candle_range).astype(float)

        # Engulfing
        bull_eng = (close.shift(1) < open_.shift(1)) & (close > open_) & (open_ <= close.shift(1)) & (close >= open_.shift(1))
        bear_eng = (close.shift(1) > open_.shift(1)) & (close < open_) & (open_ >= close.shift(1)) & (close <= open_.shift(1))
        data["CDL_ENGULFING"] = np.where(bull_eng, 100.0, np.where(bear_eng, -100.0, 0.0))

        # Hammer
        lower_shadow = np.minimum(open_, close) - low
        upper_shadow = high - np.maximum(open_, close)
        hammer = (lower_shadow >= 2 * body) & (upper_shadow <= 0.1 * candle_range) & (body > 0)
        data["CDL_HAMMER"] = hammer.astype(float) * 100.0

        # Shooting Star
        shooting_star = (upper_shadow >= 2 * body) & (lower_shadow <= 0.1 * candle_range) & (body > 0)
        data["CDL_SHOOTINGSTAR"] = shooting_star.astype(float) * -100.0

        return data
