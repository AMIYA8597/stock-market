"""Volatility and dispersion factor construction."""

from __future__ import annotations

import numpy as np
import pandas as pd

from research.feature_engineering.base import FeatureBuilder


class VolatilityFactorsBuilder(FeatureBuilder):
    """Build realized and model-inspired volatility factors."""

    name = "volatility_factors"

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        data = frame.sort_values("time").copy()
        close = data["close"].astype(float)
        high = data["high"].astype(float)
        low = data["low"].astype(float)
        open_ = data["open"].astype(float)

        log_hl = np.log(high / low.replace(0, np.nan))
        data["parkinson_vol_21d"] = (log_hl.pow(2).rolling(21, min_periods=10).mean() / (4 * np.log(2))) ** 0.5

        close_ret = np.log(close / close.shift(1))
        open_ret = np.log(open_ / close.shift(1))
        rs = np.log(high / close.replace(0, np.nan)) * np.log(high / open_.replace(0, np.nan))
        rs += np.log(low / close.replace(0, np.nan)) * np.log(low / open_.replace(0, np.nan))
        sigma_o = open_ret.rolling(21, min_periods=10).var()
        sigma_c = close_ret.rolling(21, min_periods=10).var()
        sigma_rs = rs.rolling(21, min_periods=10).mean()
        k = 0.34 / (1.34 + (21 + 1) / (21 - 1))
        data["yang_zhang_vol_21d"] = (sigma_o + k * sigma_c + (1 - k) * sigma_rs).clip(lower=0).pow(0.5)

        ewma_var = close_ret.pow(2).ewm(alpha=0.06, adjust=False).mean()
        data["ewma_garch_vol"] = ewma_var.pow(0.5)
        data["realized_vol_21d"] = close_ret.rolling(21, min_periods=10).std()
        data["realized_vol_63d"] = close_ret.rolling(63, min_periods=21).std()
        data["vol_of_vol_21d"] = data["realized_vol_21d"].rolling(21, min_periods=10).std()

        return data
