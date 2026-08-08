"""Price-derived factor construction."""

from __future__ import annotations

import numpy as np
import pandas as pd

from research.feature_engineering.base import FeatureBuilder


class PriceFactorsBuilder(FeatureBuilder):
    """Build price and momentum factors from OHLCV time series."""

    name = "price_factors"

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        if "symbol" in frame.columns and frame["symbol"].nunique() > 1:
            results = []
            for _, group in frame.groupby("symbol"):
                results.append(self._transform_single(group))
            return pd.concat(results).sort_index()
        return self._transform_single(frame)

    def _transform_single(self, frame: pd.DataFrame) -> pd.DataFrame:
        data = frame.sort_values("time").copy()
        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)

        data["ret_1d"] = np.log(close / close.shift(1))
        data["ret_2d"] = np.log(close / close.shift(2))
        data["ret_3d"] = np.log(close / close.shift(3))
        data["ret_5d"] = np.log(close / close.shift(5))
        data["ret_10d"] = np.log(close / close.shift(10))
        data["ret_20d"] = np.log(close / close.shift(20))
        data["ret_21d"] = np.log(close / close.shift(21))

        data["momentum_21d"] = close.pct_change(21)
        data["momentum_63d"] = close.pct_change(63)
        data["momentum_126d"] = close.pct_change(126)

        # Rolling moments (20d window)
        rolling_20d_ret = data["ret_1d"].rolling(20, min_periods=10)
        data["ret_mean_20d"] = rolling_20d_ret.mean()
        data["ret_std_20d"] = rolling_20d_ret.std()
        data["ret_skew_20d"] = rolling_20d_ret.skew()
        data["ret_kurt_20d"] = rolling_20d_ret.kurt()

        rolling_252_high = high.rolling(252, min_periods=21).max()
        rolling_252_low = low.rolling(252, min_periods=21).min()
        data["dist_52w_high"] = close / rolling_252_high - 1.0
        data["dist_52w_low"] = close / rolling_252_low - 1.0

        running_peak = close.cummax()
        data["drawdown"] = close / running_peak - 1.0
        data["drawdown_21d_min"] = data["drawdown"].rolling(21, min_periods=5).min()

        data["range_pct"] = (high - low) / close.replace(0, np.nan)
        data["close_to_open"] = close / data["open"].astype(float).replace(0, np.nan) - 1.0

        # Gap feature: gap from previous close to today's open
        prev_close = close.shift(1).replace(0, np.nan)
        data["gap_pct"] = data["open"].astype(float) / prev_close - 1.0

        return data
