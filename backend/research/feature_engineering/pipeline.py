"""Sequential feature engineering pipeline."""

from __future__ import annotations

import numpy as np
import pandas as pd

from research.feature_engineering.base import FeatureBuilder
from research.feature_engineering.calendar_effects import CalendarEffectsBuilder
from research.feature_engineering.cross_sectional import CrossSectionalBuilder
from research.feature_engineering.ff5_betas import FF5BetasBuilder
from research.feature_engineering.microstructure import MicrostructureBuilder
from research.feature_engineering.price_factors import PriceFactorsBuilder
from research.feature_engineering.sentiment_factors import SentimentFactorsBuilder
from research.feature_engineering.volatility_factors import VolatilityFactorsBuilder


class FeaturePipeline:
    """Compose multiple feature builders into one causality-safe pipeline."""

    def __init__(self, builders: list[FeatureBuilder] | None = None) -> None:
        self.builders = builders or [
            PriceFactorsBuilder(),
            VolatilityFactorsBuilder(),
            MicrostructureBuilder(),
            CalendarEffectsBuilder(),
            SentimentFactorsBuilder(),
            FF5BetasBuilder(),
            CrossSectionalBuilder(),
        ]

    def run(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Run all builders and return a feature-enriched frame."""
        data = frame.copy()
        for builder in self.builders:
            data = builder.fit_transform(data)

        numeric_cols = data.select_dtypes(include=[np.number]).columns
        data[numeric_cols] = data[numeric_cols].replace([np.inf, -np.inf], np.nan)
        return data
