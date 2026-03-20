"""Microstructure factor construction from trade and book proxies."""

from __future__ import annotations

import numpy as np
import pandas as pd

from research.feature_engineering.base import FeatureBuilder


class MicrostructureBuilder(FeatureBuilder):
    """Build OFI, Amihud and spread-based microstructure factors."""

    name = "microstructure"

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        data = frame.sort_values("time").copy()
        close = data["close"].astype(float)
        volume = data["volume"].astype(float).replace(0, np.nan)

        signed_flow = np.sign(close.diff().fillna(0.0)) * volume.fillna(0.0)
        data["ofi"] = signed_flow.rolling(10, min_periods=3).sum()

        ret_abs = close.pct_change().abs()
        data["amihud_illiquidity"] = ret_abs / volume
        data["amihud_21d"] = data["amihud_illiquidity"].rolling(21, min_periods=10).mean()

        bid = data["bid"].astype(float) if "bid" in data.columns else close * 0.999
        ask = data["ask"].astype(float) if "ask" in data.columns else close * 1.001
        mid = (bid + ask) / 2.0
        spread = (ask - bid) / mid.replace(0, np.nan)
        data["quoted_spread"] = spread

        delta_p = close.diff()
        delta_q = np.sign(delta_p).replace(0, np.nan)
        cov = (delta_p * delta_q).rolling(21, min_periods=10).mean()
        var_q = delta_q.rolling(21, min_periods=10).var()
        data["kyle_lambda"] = cov / var_q.replace(0, np.nan)

        data["corwin_schultz_proxy"] = np.log(data["high"].astype(float) / data["low"].astype(float).replace(0, np.nan)).rolling(2, min_periods=2).mean()

        return data
