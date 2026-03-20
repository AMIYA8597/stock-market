"""Sentiment factor construction from scored news observations."""

from __future__ import annotations

import pandas as pd

from research.feature_engineering.base import FeatureBuilder


class SentimentFactorsBuilder(FeatureBuilder):
    """Build sentiment EWMA and dispersion signals."""

    name = "sentiment_factors"

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        data = frame.copy()
        if "sentiment_score" not in data.columns:
            data["sentiment_score"] = 0.0

        score = data["sentiment_score"].astype(float)
        data["sentiment_ewm_7"] = score.ewm(span=7, adjust=False).mean()
        data["sentiment_ewm_21"] = score.ewm(span=21, adjust=False).mean()
        data["sentiment_vol_21"] = score.rolling(21, min_periods=5).std()
        data["sentiment_z_21"] = (score - score.rolling(21, min_periods=5).mean()) / score.rolling(21, min_periods=5).std().replace(0, pd.NA)

        return data
