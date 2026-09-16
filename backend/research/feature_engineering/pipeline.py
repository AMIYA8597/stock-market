"""Sequential feature engineering pipeline."""

from __future__ import annotations

import numpy as np
import pandas as pd

from research.feature_engineering.base import FeatureBuilder
from research.feature_engineering.calendar_effects import CalendarEffectsBuilder
from research.feature_engineering.chart_patterns import ChartPatternsBuilder
from research.feature_engineering.cross_sectional import CrossSectionalBuilder
from research.feature_engineering.ff5_betas import FF5BetasBuilder
from research.feature_engineering.microstructure import MicrostructureBuilder
from research.feature_engineering.price_factors import PriceFactorsBuilder
from research.feature_engineering.sentiment_factors import SentimentFactorsBuilder
from research.feature_engineering.target import TargetBuilder
from research.feature_engineering.technical_factors import TechnicalFactorsBuilder
from research.feature_engineering.volatility_factors import VolatilityFactorsBuilder


class FeaturePipeline:
    """Compose multiple feature builders into one causality-safe pipeline."""

    def __init__(self, builders: list[FeatureBuilder] | None = None) -> None:
        self.builders = builders or [
            PriceFactorsBuilder(),
            VolatilityFactorsBuilder(),
            TechnicalFactorsBuilder(),
            ChartPatternsBuilder(),
            MicrostructureBuilder(),
            CalendarEffectsBuilder(),
            SentimentFactorsBuilder(),
            FF5BetasBuilder(),
            CrossSectionalBuilder(),
            TargetBuilder(),
        ]

    def run(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Run all builders and return a feature-enriched frame."""
        data = frame.copy()
        for builder in self.builders:
            data = builder.fit_transform(data)

        numeric_cols = data.select_dtypes(include=[np.number]).columns
        data[numeric_cols] = data[numeric_cols].replace([np.inf, -np.inf], np.nan)
        return data

    def validate_causality(self, frame: pd.DataFrame) -> None:
        """Verify that the pipeline does not suffer from look-ahead bias.

        This acts as a strict leakage guard at the feature-engineering level.
        It runs the pipeline on a full dataset and a truncated dataset, and
        asserts that the features at the boundary are identical.
        """
        if len(frame) < 20:
            return

        full_features = self.run(frame)

        # Truncate the frame by removing the last 5 rows
        t_idx = len(frame) - 5
        truncated_frame = frame.iloc[:t_idx].copy()
        trunc_features = self.run(truncated_frame)

        boundary_idx = truncated_frame.index[-1]

        row_full = full_features.loc[boundary_idx]
        row_trunc = trunc_features.loc[boundary_idx]

        numeric_cols = full_features.select_dtypes(include=[np.number]).columns

        mismatches = []
        for col in numeric_cols:
            if col == "target_direction_1d":
                continue

            val_full = row_full[col]
            val_trunc = row_trunc[col]

            if pd.isna(val_full) and pd.isna(val_trunc):
                continue

            if not np.isclose(val_full, val_trunc, equal_nan=True):
                mismatches.append(f"{col} (full={val_full}, trunc={val_trunc})")

        if mismatches:
            raise ValueError(
                f"Causality guard failed! Look-ahead bias detected in features: {', '.join(mismatches)}"
            )
