"""Target label builder."""

from __future__ import annotations

import numpy as np
import pandas as pd

from research.feature_engineering.base import FeatureBuilder


class TargetBuilder(FeatureBuilder):
    """Build isolated target labels.

    Target must be strictly excluded from the final features JSON
    to prevent look-ahead bias leakage.
    """

    name = "target"

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        data = frame.sort_values("time").copy()

        # Next-day return direction: sign(close[t+1] - close[t])
        # We shift(-1) to bring t+1 into the row for t
        next_close = data["close"].shift(-1)
        data["target_direction_1d"] = np.sign(next_close - data["close"])

        return data
