"""Schemas for advanced market intelligence APIs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Literal

from pydantic import BaseModel, Field


SignalDirection = Literal["STRONG_BUY", "BUY", "NEUTRAL", "SELL", "STRONG_SELL"]


class TFTSignal(BaseModel):
    p10: float
    p50: float
    p90: float
    raw_signal: float
    horizon_days: int


class HMMGarchSignal(BaseModel):
    regime_signal: str
    vol_forecast_1d: float
    vol_forecast_21d: float


class GNNSignal(BaseModel):
    spillover_risk: float
    embedding_norm: float
    top_correlated_assets: List[str]


class LSTMAttnSignal(BaseModel):
    raw_signal: float
    attention_peaks: List[Dict[str, float]]


class XGBoostSignal(BaseModel):
    raw_signal: float
    top_features: List[Dict[str, float | str]]


class EnsembleSignal(BaseModel):
    signal: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    direction: SignalDirection
    kelly_fraction: float = Field(ge=0.0, le=1.0)


class RegimeDetails(BaseModel):
    state: Literal["BULL", "BEAR", "SIDEWAYS", "CRISIS"]
    probs: Dict[str, float]
    transition_probs: Dict[str, float]


class SignalResponse(BaseModel):
    symbol: str
    timestamp: datetime
    ensemble: EnsembleSignal
    models: Dict[str, TFTSignal | HMMGarchSignal | GNNSignal | LSTMAttnSignal | XGBoostSignal]
    model_weights: Dict[str, float]
    regime: RegimeDetails


class SignalHistoryPoint(BaseModel):
    timestamp: datetime
    signal: float
    actual_return: float
    model: str


class RegimeCurrentResponse(BaseModel):
    state: Literal["BULL", "BEAR", "SIDEWAYS", "CRISIS"]
    probs: Dict[str, float]
    transition_matrix: List[List[float]]
    cond_vol_1d: float
    cond_vol_5d: float
    cond_vol_21d: float
    days_in_state: int
    last_transition_date: date


class RegimeHistoryPoint(BaseModel):
    time: date
    state: Literal["BULL", "BEAR", "SIDEWAYS", "CRISIS"]
    probs: Dict[str, float]
    cond_vol: float


class RegimeStatisticsItem(BaseModel):
    state: Literal["BULL", "BEAR", "SIDEWAYS", "CRISIS"]
    avg_duration: float
    avg_return: float
    avg_vol: float
    freq: float


class SHAPContribution(BaseModel):
    name: str
    shap_val: float
    feature_val: float
    pct_rank: float


class ExplainShapResponse(BaseModel):
    model: Literal["xgboost"]
    feature_contributions: List[SHAPContribution]
    base_value: float
    output_value: float
    waterfall_ready: bool


class AttentionTopTimestep(BaseModel):
    date: date
    weight: float


class ExplainAttentionResponse(BaseModel):
    model: Literal["tft", "lstm_attn"]
    weights: List[List[float]]
    mean_weights: List[float]
    top_timesteps: List[AttentionTopTimestep]


class CounterfactualFeatureChange(BaseModel):
    name: str
    original: float
    counterfactual: float


class CounterfactualResponse(BaseModel):
    cf_id: str
    changed_features: List[CounterfactualFeatureChange]
    resulting_signal: SignalDirection
    proximity_score: float


class CounterfactualRequest(BaseModel):
    target_direction: Literal["BUY", "SELL"]
    num_cfs: int = Field(ge=1, le=10, default=5)


class ModelAccuracyItem(BaseModel):
    model: Literal["tft", "hmm_garch", "gnn", "lstm_attn", "xgboost", "ensemble"]
    precision: float
    recall: float
    directional_accuracy: float
    p50_rmse: float
    winkler_coverage_score: float


class DriftItem(BaseModel):
    model: Literal["tft", "hmm_garch", "gnn", "lstm_attn", "xgboost", "ensemble"]
    adwin_p_value: float
    drift_detected: bool
    residual_distribution: List[float]
    ks_stat: float


class EnsembleWeightPoint(BaseModel):
    date: date
    tft: float
    hmm_garch: float
    gnn: float
    lstm_attn: float
    xgboost: float


class EconomicCalendarEvent(BaseModel):
    date: date
    category: Literal["FOMC", "EARNINGS", "EXPIRY", "MACRO"]
    title: str
    impact: Literal["LOW", "MEDIUM", "HIGH"]


class CorrelationNode(BaseModel):
    ticker: str
    sector: str
    x: float
    y: float
    size: float


class CorrelationEdge(BaseModel):
    source: str
    target: str
    correlation: float


class CorrelationGraphResponse(BaseModel):
    window_days: int
    central_asset: str
    nodes: List[CorrelationNode]
    edges: List[CorrelationEdge]
    top_correlates: List[Dict[str, float | str]]


class FactorExposureItem(BaseModel):
    factor: str
    beta: float


class FactorExposureResponse(BaseModel):
    symbol: str
    window_days: int
    exposures: List[FactorExposureItem]
    metrics: Dict[str, float]
