"""Calendar and seasonality feature construction."""

from __future__ import annotations

import numpy as np
import pandas as pd

from research.feature_engineering.base import FeatureBuilder


class CalendarEffectsBuilder(FeatureBuilder):
    """Build cyclical calendar features and event proximity signals."""

    name = "calendar_effects"

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        data = frame.copy()
        t = pd.to_datetime(data["time"], utc=True)

        dow = t.dt.dayofweek.astype(float)
        month = t.dt.month.astype(float)
        dom = t.dt.day.astype(float)

        data["dow_sin"] = np.sin(2 * np.pi * dow / 7.0)
        data["dow_cos"] = np.cos(2 * np.pi * dow / 7.0)
        data["month_sin"] = np.sin(2 * np.pi * month / 12.0)
        data["month_cos"] = np.cos(2 * np.pi * month / 12.0)
        data["dom_sin"] = np.sin(2 * np.pi * dom / 31.0)
        data["dom_cos"] = np.cos(2 * np.pi * dom / 31.0)

        data["is_month_end"] = t.dt.is_month_end.astype(int)
        data["is_quarter_end"] = t.dt.is_quarter_end.astype(int)
        data["is_year_end"] = t.dt.is_year_end.astype(int)

        # Deterministic event proximity proxy.
        earnings_anchor_day = 15
        data["days_to_earnings_proxy"] = (earnings_anchor_day - dom).abs()

        return data
