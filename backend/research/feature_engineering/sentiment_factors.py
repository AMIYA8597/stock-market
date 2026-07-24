"""Sentiment factor construction from scored news observations."""

from __future__ import annotations

import pandas as pd

from research.feature_engineering.base import FeatureBuilder


class SentimentFactorsBuilder(FeatureBuilder):
    """Build sentiment EWMA and dispersion signals."""

    name = "sentiment_factors"

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        data = frame.copy()

        # We expect sentiment_score, news_volume, sentiment_pos_neg_ratio, market_sentiment_index
        # to be merged in from feature_tasks.py.
        # Ensure they exist and fall back to 0.0 if not.
        for col in ["sentiment_score", "news_volume", "sentiment_pos_neg_ratio", "market_sentiment_index"]:
            if col not in data.columns:
                data[col] = 0.0

        score = data["sentiment_score"].astype(float)

        # In feature_tasks, the sentiment_score is day-t. If we are on day-t, we can use it directly
        # BUT because we want to predict day t+1, it's safe to use the sentiment of day t.
        # We add 3-day momentum:
        data["sentiment_ewm_7"] = score.ewm(span=7, adjust=False).mean()
        data["sentiment_ewm_21"] = score.ewm(span=21, adjust=False).mean()
        data["sentiment_vol_21"] = score.rolling(21, min_periods=5).std()
        data["sentiment_z_21"] = (score - score.rolling(21, min_periods=5).mean()) / score.rolling(
            21, min_periods=5
        ).std().replace(0, pd.NA)

        # 3-day sentiment momentum
        data["sentiment_mom_3"] = score - score.shift(3)

        return data
