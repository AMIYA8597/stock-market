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

        # Expiry Week proxy (approximate last Thursday of the month)
        # Week number of the month (approximate)
        last_day_of_month = t + pd.offsets.MonthEnd(0)
        # Find the last Thursday of the month
        last_thursday = last_day_of_month - pd.to_timedelta(
            (last_day_of_month.dt.dayofweek - 3) % 7, unit="d"
        )
        # If current week is the week of last Thursday
        data["is_expiry_week"] = (
            t.dt.isocalendar().week == last_thursday.dt.isocalendar().week
        ).astype(int)

        # Holiday proximity (approximate NSE holidays which are often Mondays/Fridays)
        # Flagging days that are next to weekends as higher probability of being pre/post holiday
        data["is_pre_holiday"] = (dow == 4).astype(int)  # Friday
        data["is_post_holiday"] = (dow == 0).astype(int)  # Monday

        return data
