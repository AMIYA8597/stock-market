"""Feature Registry and API for unified ML pipeline."""

import pandas as pd
from datetime import datetime
from typing import Literal, Optional, List, Dict, Any
import numpy as np

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
from research.feature_engineering.pipeline import FeaturePipeline

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
        source_columns: List[str],
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
        TargetBuilder(),
    ])

def build_features(
    data: pd.DataFrame, 
    as_of: Optional[pd.Timestamp | str] = None, 
    mode: Literal["research", "serving"] = "serving"
) -> pd.DataFrame:
    """
    Core function to build features identically for training (research) and live (serving).
    Enforces V2-1 Point-in-time constraints.
    """
    df = data.copy()
    
    if as_of is not None:
        as_of_ts = pd.to_datetime(as_of)
        # Assuming index is datetime or there is a 'time'/'date' column
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
    
    # In research mode, we might do causality checks
    if mode == "research" and len(df) >= 20:
        pipeline.validate_causality(df)
        
    features = pipeline.run(df)
    
    # Target column handling: Drop target in serving mode
    if mode == "serving":
        target_cols = [c for c in features.columns if c.startswith("target_")]
        features = features.drop(columns=target_cols)
        
    return features
