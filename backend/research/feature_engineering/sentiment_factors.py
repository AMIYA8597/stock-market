"""Sentiment factor construction from scored news observations."""

from __future__ import annotations

import pandas as pd

from research.feature_engineering.base import FeatureBuilder


class SentimentFactorsBuilder(FeatureBuilder):
    """Build sentiment EWMA and dispersion signals."""

    name = "sentiment_factors"

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        data = frame.copy()

        # Ensure sentiment features exist, and STRICTLY shift by 1 to prevent intraday/after-hours leakage.
        # News published on day T cannot be used to predict day T if processed after market close.
        sentiment_cols = [
            "sentiment_score",
            "news_volume",
            "sentiment_pos_neg_ratio",
            "market_sentiment_index",
        ]

        # First ensure they exist
        for col in sentiment_cols:
            if col not in data.columns:
                data[col] = 0.0

        # Group by symbol if panel data, else just shift
        if "symbol" in data.columns:
            data = data.sort_values(["symbol", "time"])
            for col in sentiment_cols:
                data[col] = data.groupby("symbol")[col].shift(1).fillna(0.0)
        else:
            data = data.sort_values("time")
            for col in sentiment_cols:
                data[col] = data[col].shift(1).fillna(0.0)

        score = data["sentiment_score"].astype(float)
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
