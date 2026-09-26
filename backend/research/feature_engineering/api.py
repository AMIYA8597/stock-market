"""Feature Registry and API for unified ML pipeline."""

from typing import Literal

import pandas as pd

from research.feature_engineering.calendar_effects import CalendarEffectsBuilder
from research.feature_engineering.chart_patterns import ChartPatternsBuilder
from research.feature_engineering.microstructure import MicrostructureBuilder
from research.feature_engineering.pipeline import FeaturePipeline
from research.feature_engineering.price_factors import PriceFactorsBuilder
from research.feature_engineering.sentiment_factors import SentimentFactorsBuilder
from research.feature_engineering.technical_factors import TechnicalFactorsBuilder
from research.feature_engineering.volatility_factors import VolatilityFactorsBuilder


class FeatureManifest:
    """Registry definition for features."""
    def __init__(
        self,
        feature_id: str,
        name: str,
        version: str,
        category: str,
        lookback: int,
        warmup: int,
        source_columns: list[str],
        availability_delay: str = "T+0",
        uses_cross_section: bool = False,
        uses_news: bool = False,
        uses_external_data: bool = False,
        fit_required: bool = False,
        transform_hash: str = "v1",
        production_status: str = "active"
    ):
        self.feature_id = feature_id
        self.name = name
        self.version = version
        self.category = category
        self.lookback = lookback
        self.warmup = warmup
        self.source_columns = source_columns
        self.availability_delay = availability_delay
        self.uses_cross_section = uses_cross_section
        self.uses_news = uses_news
        self.uses_external_data = uses_external_data
        self.fit_required = fit_required
        self.transform_hash = transform_hash
        self.production_status = production_status

def get_canonical_pipeline() -> FeaturePipeline:
    """Returns the one canonical feature pipeline for both research and serving."""
    return FeaturePipeline([
        PriceFactorsBuilder(),
        VolatilityFactorsBuilder(),
        TechnicalFactorsBuilder(),
        ChartPatternsBuilder(),
        MicrostructureBuilder(),
        CalendarEffectsBuilder(),
        SentimentFactorsBuilder(),
        # CrossSectionalBuilder(), # Needs multi-asset context
        # FF5BetasBuilder(),       # Needs Fama-French context
    ])

def build_features(
    data: pd.DataFrame,
    as_of: pd.Timestamp | str | None = None,
    mode: Literal["research", "serving"] = "serving"
) -> pd.DataFrame:
    """
    Core function to build features identically for training (research) and live (serving).
    Enforces V2-1 Point-in-time constraints.
    """
    df = data.copy()

    if as_of is not None:
        as_of_ts = pd.to_datetime(as_of)
        if isinstance(df.index, pd.DatetimeIndex):
            df = df[df.index <= as_of_ts].copy()
        elif 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
            df = df[df['time'] <= as_of_ts].copy()
        elif 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df[df['date'] <= as_of_ts].copy()

    if len(df) == 0:
        return df

    pipeline = get_canonical_pipeline()

    if mode == "research" and len(df) >= 20:
        pipeline.validate_causality(df)

    features = pipeline.run(df)
    return features
