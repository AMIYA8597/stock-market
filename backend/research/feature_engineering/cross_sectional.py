"""Cross-sectional normalization and sector-relative factors."""

from __future__ import annotations

import numpy as np
import pandas as pd

from research.feature_engineering.base import FeatureBuilder


class CrossSectionalBuilder(FeatureBuilder):
    """Build rank and z-score factors across symbols for each timestamp."""

    name = "cross_sectional"

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        if "symbol" not in frame.columns:
            return frame

        data = frame.copy()
        key_cols = [col for col in ["ret_1d", "momentum_21d", "realized_vol_21d", "amihud_21d"] if col in data.columns]

        for col in key_cols:
            grouped = data.groupby("time")[col]
            mean = grouped.transform("mean")
            std = grouped.transform("std").replace(0, np.nan)
            data[f"{col}_zscore"] = (data[col] - mean) / std
            data[f"{col}_rank"] = grouped.rank(pct=True)

        if "sector" in data.columns and "ret_1d" in data.columns:
            sector_mean = data.groupby(["time", "sector"])["ret_1d"].transform("mean")
            data["ret_1d_sector_relative"] = data["ret_1d"] - sector_mean

        return data.replace([np.inf, -np.inf], np.nan)
