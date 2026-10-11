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
            # TargetBuilder() is explicitly removed from the default feature pipeline
            # per Stage 3 V3 Requirements.
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
        """Verify that feature rows are invariant to information after their cutoff."""
        if len(frame) < 20:
            return

        full_features = self.run(frame)
        numeric_cols = [
            col
            for col in full_features.select_dtypes(include=[np.number]).columns
            if not col.startswith("target_")
        ]
        boundaries = sorted({len(frame) - 1, *range(19, len(frame), max(1, len(frame) // 10))})

        for boundary in boundaries:
            cutoff = frame.iloc[: boundary + 1].copy()
            truncated = self.run(cutoff)
            boundary_index = cutoff.index[-1]
            mismatches = self._causality_mismatches(
                full_features.loc[boundary_index], truncated.loc[boundary_index], numeric_cols
            )

            if boundary + 1 < len(frame):
                perturbed = frame.copy()
                future_rows = perturbed.index[boundary + 1 :]
                for column in ("open", "high", "low", "close", "volume"):
                    if column in perturbed.columns:
                        perturbed.loc[future_rows, column] = perturbed.loc[future_rows, column] * 1.37
                perturbed_features = self.run(perturbed)
                mismatches.extend(
                    self._causality_mismatches(
                        full_features.loc[boundary_index],
                        perturbed_features.loc[boundary_index],
                        numeric_cols,
                    )
                )

            if mismatches:
                raise ValueError(
                    "Causality guard failed! Look-ahead bias detected in features: "
                    + ", ".join(dict.fromkeys(mismatches))
                )

    @staticmethod
    def _causality_mismatches(
        expected: pd.Series, actual: pd.Series, columns: list[str]
    ) -> list[str]:
        mismatches = []
        for column in columns:
            if column not in expected.index or column not in actual.index:
                continue
            expected_value = expected[column]
            actual_value = actual[column]
            if pd.isna(expected_value) and pd.isna(actual_value):
                continue
            try:
                close = np.isclose(float(expected_value), float(actual_value), equal_nan=True)
            except (TypeError, ValueError):
                close = expected_value == actual_value
            if not close:
                mismatches.append(f"{column} (full={expected_value}, truncated={actual_value})")
        return mismatches
