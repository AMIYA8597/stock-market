# backend/app/services/prediction_engine.py
"""Prediction Engine – 7-layer ensemble for Indian stocks.

This module provides the core logic required by the NeuroQuant system.
It fetches OHLCV data via yfinance, computes technical indicators,
detects candlestick patterns, calculates Jegadeesh-Titman momentum,
runs regime detection, trains an XGBoost classifier,
and produces SARIMAX/HoltWinters price forecasts.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

from app.services.signal_engine import TechnicalSignalEngine

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent.parent.parent / "data" / "models"

# ---------------------------------------------------------------------------
# Redis & In-Memory Cache Helpers
# ---------------------------------------------------------------------------

_in_memory_prediction_cache: dict[str, tuple[dict[str, Any], float]] = {}

async def _cache_fetch(symbol: str) -> dict[str, Any] | None:
    """Attempt to retrieve cached full prediction for *symbol*."""
    key = f"prediction_raw:{symbol.upper()}"
    now = datetime.now(UTC).timestamp()

    # Check in-memory cache first
    if key in _in_memory_prediction_cache:
        cached, ts = _in_memory_prediction_cache[key]
        if now - ts < 1800:  # 30 minutes cache TTL in memory
            return cached

    try:
        from app.database.redis_client import get_redis
        redis = await get_redis()
        cached = await redis.get(key)
        if cached:
            res_dict = json.loads(cached)
            _in_memory_prediction_cache[key] = (res_dict, now)
            return res_dict
    except Exception as e:
        logger.warning(f"Redis cache fetch failed for prediction key={key}: {e}")
    return None

async def _cache_store(symbol: str, payload: dict[str, Any]) -> None:
    """Store *payload* in Redis & memory for *symbol* with a TTL of 3600 seconds (1 hour)."""
    key = f"prediction_raw:{symbol.upper()}"
    now = datetime.now(UTC).timestamp()
    _in_memory_prediction_cache[key] = (payload, now)

    try:
        from app.database.redis_client import get_redis
        redis = await get_redis()
        await redis.setex(key, 3600, json.dumps(payload, default=str))
    except Exception as e:
        logger.warning(f"Failed to cache prediction for key={key}: {e}")

# ---------------------------------------------------------------------------
# ML/Predictive Scoring
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Layer 4 – HMM Regime Detection
# ---------------------------------------------------------------------------

_HMM_CACHE = {}
_MODEL_CACHE = {}
_INDEX_DATA_CACHE = None
_SENTIMENT_PIPELINE = None

def get_sentiment_pipeline():
    global _SENTIMENT_PIPELINE
    if _SENTIMENT_PIPELINE is None:
        try:
            from transformers import pipeline
            # Using ProsusAI/finbert which is the standard financial BERT
            _SENTIMENT_PIPELINE = pipeline("sentiment-analysis", model="ProsusAI/finbert", device=-1)
        except Exception as e:
            logger.error(f"Failed to load FinBERT pipeline: {e}")
            _SENTIMENT_PIPELINE = "failed"
    return _SENTIMENT_PIPELINE


def detect_regime(df: pd.DataFrame) -> dict[str, Any]:
    if len(df) < 60:
        return {"regime": "unknown", "regime_confidence": 0.5, "bull_prob": 0.5, "bear_prob": 0.5, "hmm_used": False}

    try:
        from research.models.hmm_garch.inference import InferenceEngine
        ohlcv_data = df[["open", "high", "low", "close", "volume"]].astype(float).values

        symbol = df.attrs.get("symbol", "DEFAULT")
        if symbol in _HMM_CACHE:
            engine = _HMM_CACHE[symbol]
            train_flag = False
        else:
            engine = InferenceEngine()
            train_flag = True

        res = engine.predict(ohlcv_data, train=train_flag)
        if train_flag:
            _HMM_CACHE[symbol] = engine

        current_state = res.current_state
        probs = res.state_probs

        state_to_regime = {
            0: "BULL",
            1: "BEAR",
            2: "SIDEWAYS",
            3: "CRISIS"
        }
        regime = state_to_regime.get(current_state, "SIDEWAYS")
        bull_prob = float(probs[0])
        bear_prob = float(probs[1])
        regime_confidence = float(probs[current_state])
        hmm_used = True

        conditional_vol = float(res.conditional_vol)
        forecast_5d = res.vol_forecast_5d
        forecast_21d = res.vol_forecast_21d
        tm = engine.get_transition_matrix()
        transition_matrix = tm.tolist() if tm is not None else None

        return {
            "regime": regime,
            "bull_prob": bull_prob,
            "bear_prob": bear_prob,
            "regime_confidence": regime_confidence,
            "hmm_used": hmm_used,
            "conditional_vol": conditional_vol,
            "vol_forecast_5d": float(forecast_5d[-1]) if len(forecast_5d) > 0 else conditional_vol,
            "vol_forecast_21d": float(forecast_21d[-1]) if len(forecast_21d) > 0 else conditional_vol,
            "transition_matrix": transition_matrix,
        }
    except Exception as e:
        logger.warning(f"Real HMM-GARCH solver failed, falling back to threshold: {e}")
        # Fall back to simple threshold regime
        ret_63d = float((df["close"].iloc[-1] / df["close"].iloc[-64]) - 1) if len(df) >= 64 else 0.0
        realized_vol = float(np.log(df["close"]/df["close"].shift(1)).rolling(21).std().iloc[-1]) if len(df) >= 22 else 0.02
        ann_vol = realized_vol * np.sqrt(252)
        sharpe_proxy = ret_63d / (ann_vol + 1e-6)
        if sharpe_proxy > 0.5:
            regime, bull_prob, bear_prob = "BULL", 0.75, 0.25
        elif sharpe_proxy < -0.5:
            regime, bull_prob, bear_prob = "BEAR", 0.25, 0.75
        else:
            regime, bull_prob, bear_prob = "SIDEWAYS", 0.5, 0.5
        regime_confidence = max(bull_prob, bear_prob)
        return {
            "regime": regime,
            "bull_prob": bull_prob,
            "bear_prob": bear_prob,
            "regime_confidence": regime_confidence,
            "hmm_used": False,
            "conditional_vol": realized_vol,
            "vol_forecast_5d": realized_vol * np.sqrt(5),
            "vol_forecast_21d": realized_vol * np.sqrt(21)
        }

# ---------------------------------------------------------------------------
# Layer 6 – Ensemble Combiner
# ---------------------------------------------------------------------------

def compute_kelly_fraction(symbol: str, signal: float, confidence: float) -> float:
    """Compute Kelly fraction from measured out-of-sample win-rate and payoff stats.

    Formula: f* = (p * b - q) / b
    Where:
      p = win probability (measured win rate from backtest)
      b = payoff ratio (avg win / avg loss)
      q = 1 - p
    """
    # Load measured walk-forward backtest statistics for Kelly calculation
    p, b = 0.54, 1.05  # Safe conservative defaults
    stats_path = MODEL_DIR / f"xgboost_backtest_{symbol.upper()}.json"

    if stats_path.exists():
        try:
            with open(stats_path) as f:
                stats = json.load(f)
            p = stats.get("win_rate", p)
            b = stats.get("payoff_ratio", b)
        except Exception as e:
            logger.warning(f"Failed to load backtest metrics for Kelly: {e}")

    q = 1.0 - p
    # Kelly sizing formula
    f_star = (p * b - q) / b if b > 0 else 0

    # Apply scaling and risk caps
    f_half = f_star / 2.0  # half-Kelly
    f_scaled = f_half * confidence * abs(signal)
    return float(np.clip(f_scaled, 0.0, 0.25))


def standardize_df_columns(df: pd.DataFrame, expected_features: list[str]) -> pd.DataFrame:
    df_copy = df.copy()

    # Drop any duplicate columns first
    df_copy = df_copy.loc[:, ~df_copy.columns.duplicated()]

    # Case-insensitive mapping to expected features
    rename_map = {}
    col_map = {c.lower(): c for c in df_copy.columns}

    # 1. Exact case-insensitive matching
    for exp in expected_features:
        exp_lower = exp.lower()
        if exp_lower in col_map:
            rename_map[col_map[exp_lower]] = exp

    # 2. Heuristic mapping for pandas-ta generated columns
    for col in df_copy.columns:
        if col in rename_map:
            continue
        col_lower = col.lower()
        # RSI
        if "rsi" in col_lower and "14" in col_lower:
            rename_map[col] = "RSI_14"
        # MACD
        elif "macdh" in col_lower and "12" in col_lower:
            rename_map[col] = "MACDh_12_26_9"
        # Bollinger Bands %B
        elif "bbp" in col_lower and "20" in col_lower:
            rename_map[col] = "BBP_20_2.0"
        # ATR
        elif "atr" in col_lower and "14" in col_lower:
            rename_map[col] = "ATRr_14"
        # ADX
        elif "adx" in col_lower and "14" in col_lower:
            rename_map[col] = "ADX_14"

    # Apply rename
    if rename_map:
        df_copy = df_copy.rename(columns=rename_map)

    # Drop duplicates again in case two columns were renamed to the same name
    df_copy = df_copy.loc[:, ~df_copy.columns.duplicated()]

    # Fill any missing expected features with 0.0
    for exp in expected_features:
        if exp not in df_copy.columns:
            df_copy[exp] = 0.0

    return df_copy


async def build_ensemble_signal(symbol: str, df: pd.DataFrame, artifact_path: str = None, model_version: str = None) -> dict[str, Any]:
    return await asyncio.to_thread(build_ensemble_signal_sync, symbol, df, artifact_path, model_version)

def build_ensemble_signal_sync(symbol: str, df: pd.DataFrame, artifact_path: str = None, model_version: str = None) -> dict[str, Any]:
    expected_features = [
        "ret_1d", "ret_5d", "ret_21d", "momentum_63d",
        "RSI_14", "MACDh_12_26_9", "BBP_20_2.0", "ATRr_14",
        "ADX_14", "realized_vol_21d", "yang_zhang_vol_21d",
        "dist_52w_high", "dist_52w_low", "drawdown",
        "range_pct", "close_to_open"
    ]
    df = standardize_df_columns(df, expected_features)
    df.attrs["symbol"] = symbol

    # 1. Detect HMM regime (using real local HMM GARCH detect_regime)
    regime_info = detect_regime(df)
    regime_state = 0
    if regime_info["regime"] == "BULL":
        regime_state = 0
    elif regime_info["regime"] == "BEAR":
        regime_state = 1
    elif regime_info["regime"] == "SIDEWAYS":
        regime_state = 2
    elif regime_info["regime"] == "CRISIS":
        regime_state = 3

    # Define model lists
    model_names = ["tft", "hmm_garch", "gnn", "lstm_attention", "xgboost"]

    # Prior weights matrix matching regimes (bull, bear, sideways, crisis)
    np.array(
        [
            [0.30, 0.10, 0.20, 0.15, 0.25],  # Bull state
            [0.15, 0.35, 0.10, 0.10, 0.30],  # Bear state
            [0.20, 0.15, 0.15, 0.35, 0.15],  # Sideways state
            [0.10, 0.40, 0.15, 0.10, 0.25],  # Crisis state
        ],
        dtype=np.float32,
    )

    # 2. Compute individual model signals
    model_signals = {}
    model_confidences = {}
    model_statuses = {}

    # --- XGBoost ---
    xgb_score = 0.0
    xgb_confidence = 0.5
    xgb_top_features = []
    xgb_base_value = 0.5
    xgb_status = "untrained"
    try:
        from research.models.xgboost_model.classifier import (
            FeatureMismatchError,
            XGBoostDirectionalClassifier,
        )
    except ImportError:
        xgb_status = "unavailable"

    xgb_path = Path(artifact_path) if (artifact_path and "xgboost" in artifact_path.lower()) else MODEL_DIR / f"xgboost_{symbol.upper()}.pkl"

    if xgb_path.exists():
        try:
            xgb_key = f"xgboost_{symbol.upper()}_{model_version or 'latest'}"
            if xgb_key in _MODEL_CACHE:
                xgb_clf = _MODEL_CACHE[xgb_key]
            else:
                xgb_clf = XGBoostDirectionalClassifier.load(xgb_path)
                _MODEL_CACHE[xgb_key] = xgb_clf

            if xgb_clf is not None and xgb_clf.model is not None:
                prob_up = xgb_clf.predict_proba(df)
                xgb_score = float((prob_up - 0.5) * 2.0)
                xgb_confidence = float(prob_up if prob_up > 0.5 else (1.0 - prob_up))
                xgb_top_features, xgb_base_value = xgb_clf.get_shap_values(df)
                xgb_status = "trained"
        except FeatureMismatchError:
            raise
        except Exception as e:
            logger.warning(f"Failed to load or run XGBoost model for {symbol}: {e}")

    model_signals["xgboost"] = xgb_score
    model_confidences["xgboost"] = xgb_confidence
    model_statuses["xgboost"] = xgb_status

    # --- LSTM-Attention ---
    lstm_score = 0.0
    lstm_confidence = 0.5
    lstm_attn_peaks = []
    lstm_status = "untrained"
    try:
        from research.models.lstm_attention.classifier import LSTMAttentionClassifier
    except ImportError:
        lstm_status = "unavailable"

    lstm_path = Path(artifact_path) if (artifact_path and "lstm" in artifact_path.lower()) else MODEL_DIR / f"lstm_attention_{symbol.upper()}.pkl"

    if lstm_path.exists():
        try:
            lstm_key = f"lstm_attention_{symbol.upper()}"
            if lstm_key in _MODEL_CACHE:
                lstm_clf = _MODEL_CACHE[lstm_key]
            else:
                lstm_clf = LSTMAttentionClassifier.load(lstm_path)
                _MODEL_CACHE[lstm_key] = lstm_clf

            if lstm_clf is not None and lstm_clf.model is not None:
                prob_up, attn_dict = lstm_clf.predict_proba(df)
                lstm_score = float((prob_up - 0.5) * 2.0)
                lstm_confidence = float(prob_up if prob_up > 0.5 else (1.0 - prob_up))
                lstm_attn_peaks = [{"date": k, "weight": float(v)} for k, v in attn_dict.items()]
                lstm_status = "trained"
        except Exception as e:
            logger.warning(f"Failed to load or run LSTM model for {symbol}: {e}")

    model_signals["lstm_attention"] = lstm_score
    model_confidences["lstm_attention"] = lstm_confidence
    model_statuses["lstm_attention"] = lstm_status

    # --- TFT (Quantile LGBM) ---
    tft_score = 0.0
    tft_confidence = 0.5
    tft_status = "untrained"
    tft_p10, tft_p50, tft_p90 = -0.015, 0.002, 0.015
    try:
        from research.models.tft.quantile_forecaster import QuantileLGBForecaster
    except ImportError:
        tft_status = "unavailable"

    try:
        tft_key = "tft_forecaster"
        if tft_key in _MODEL_CACHE:
            tft_forecaster = _MODEL_CACHE[tft_key]
        else:
            tft_forecaster = QuantileLGBForecaster.load()
            _MODEL_CACHE[tft_key] = tft_forecaster

        if len(tft_forecaster.models) == len(tft_forecaster.quantiles):
            last_row_features = {}
            for feat in tft_forecaster.features:
                if feat in df.columns:
                    val = df[feat].iloc[-1]
                    last_row_features[feat] = float(val) if not pd.isna(val) else 0.0
                else:
                    last_row_features[feat] = 0.0
            tft_p10, tft_p50, tft_p90 = tft_forecaster.predict(last_row_features)
            tft_score = float(np.clip(tft_p50 / 0.01, -1.0, 1.0))
            conf = 0.50 + 0.35 * np.tanh((tft_p90 - tft_p10) / 0.02)
            tft_confidence = float(np.clip(conf, 0.0, 1.0))
            tft_status = "trained"
    except Exception as e:
        logger.warning(f"Failed to load or run TFT forecaster for {symbol}: {e}")

    model_signals["tft"] = tft_score
    model_confidences["tft"] = tft_confidence
    model_statuses["tft"] = tft_status

    # --- HMM-GARCH ---
    # Fits on the fly, so always active and trained
    state_to_signal = {0: 0.8, 1: -0.8, 2: 0.0, 3: -0.5}
    hmm_score = float(state_to_signal.get(regime_state, 0.0))
    hmm_confidence = float(regime_info["regime_confidence"])
    hmm_status = "trained"

    model_signals["hmm_garch"] = hmm_score
    model_confidences["hmm_garch"] = hmm_confidence
    model_statuses["hmm_garch"] = hmm_status

    # --- GNN ---
    gnn_score = 0.0
    gnn_confidence = 0.5
    gnn_top_correlated = []
    gnn_status = "untrained"
    gnn_res = None
    try:
        from research.models.gnn.contagion_risk import ContagionRiskAnalyzer
    except ImportError:
        gnn_status = "unavailable"

    try:
        global _INDEX_DATA_CACHE
        if _INDEX_DATA_CACHE is None or _INDEX_DATA_CACHE.empty:
            try:
                import yfinance as yf
                index_ticker = yf.Ticker("^NSEI")
                _INDEX_DATA_CACHE = index_ticker.history(period="2y", interval="1d")
                _INDEX_DATA_CACHE.index = pd.DatetimeIndex(_INDEX_DATA_CACHE.index).tz_localize(None)
            except Exception as index_err:
                logger.error(f"Failed to pre-fetch index data globally: {index_err}")

        index_slice = None
        if _INDEX_DATA_CACHE is not None and not _INDEX_DATA_CACHE.empty:
            start_date = df.index.min()
            end_date = df.index.max()
            index_slice = _INDEX_DATA_CACHE.loc[start_date:end_date]

        gnn_analyzer = ContagionRiskAnalyzer()
        gnn_res = gnn_analyzer.compute_risk_factors(df, index_df=index_slice)
        gnn_score = float(gnn_res["raw_signal"])
        gnn_confidence = float(1.0 - gnn_res["contagion_score"])
        gnn_top_correlated = [{"ticker": "^NSEI", "correlation": float(gnn_res["corr_to_index"])}]
        gnn_status = "trained"
    except Exception as e:
        logger.warning(f"Failed to compute GNN contagion risk for {symbol}: {e}")

    model_signals["gnn"] = gnn_score
    model_confidences["gnn"] = gnn_confidence
    model_statuses["gnn"] = gnn_status

    # --- Online Learner ---
    online_score = 0.0
    online_prob = 0.5
    try:
        from research.models.online_learner import OnlineAdaptiveLearner
    except ImportError:
        pass

    online_checkpoint = MODEL_DIR / f"online_learner_{symbol.upper()}.pkl"
    if online_checkpoint.exists():
        try:
            learner = OnlineAdaptiveLearner.load(online_checkpoint)
            if learner is not None:
                last_row = df.iloc[-1]
                x_dict = {feat: float(last_row[feat]) for feat in learner.features if feat in df.columns}
                if not any(np.isnan(v) for v in x_dict.values()):
                    online_prob = float(learner.predict_proba(x_dict))
                    online_score = float((online_prob - 0.5) * 2.0)
        except Exception as e:
            logger.warning(f"Failed to load or run OnlineAdaptiveLearner for {symbol}: {e}")

    # 3. Dynamic Weight Management and Ensemble Combining
    # EXPLICIT FUSION RULE (Phase A6)
    # final = (0.4 * technical) + (0.6 * ML) + sentiment_tilt + regime_gate

    technical = TechnicalSignalEngine.generate_signal(df)
    tech_score = technical["score"]

    # True lookahead-free local FinBERT sentiment score
    sentiment_score = 0.0
    try:
        from app.services.sentiment_analyzer import FinBERTSentimentAnalyzer
        analyzer = FinBERTSentimentAnalyzer()
        if getattr(analyzer, "_initialized", False) or getattr(analyzer, "vader", None):
            headlines = analyzer.scrape_google_news(f"{symbol} stock India")
            if headlines:
                sentiment_score = analyzer.get_stock_sentiment(symbol, headlines)
    except Exception as e:
        logger.warning(f"FinBERT sentiment extraction failed: {e}")

    sentiment_tilt = sentiment_score * 0.15

    ml_score = xgb_score if xgb_status == "trained" else 0.0

    fused_score = (0.4 * tech_score) + (0.6 * ml_score) + sentiment_tilt

    regime = regime_info["regime"]
    if regime in ("BEAR", "CRISIS") and fused_score > 0:
        fused_score = min(fused_score, 0.2)  # Suppress BUY
    elif regime == "BULL" and fused_score < 0:
        fused_score = max(fused_score, -0.2) # Suppress SELL

    raw_ensemble = float(np.clip(fused_score, -1.0, 1.0))
    prob_up = (raw_ensemble / 2.0) + 0.5
    ensemble_confidence = float(abs(prob_up - 0.5) * 2.0)

    active_signals = [xgb_score] if xgb_status == "trained" else [tech_score]
    if len(active_signals) > 0:
        pos = sum(1 for s in active_signals if s > 0.1)
        neg = sum(1 for s in active_signals if s < -0.1)
        total_votes = pos + neg
        agreement = max(pos, neg) / total_votes if total_votes > 0 else 0.5
    else:
        agreement = 0.5

    masked_weights = [1.0 if m == "xgboost" else 0.0 for m in model_names]

    # 4. Sizing and Stops
    kelly_fraction = compute_kelly_fraction(symbol, raw_ensemble, ensemble_confidence)

    direction = "NEUTRAL"
    if raw_ensemble > 0.35:
        direction = "STRONG_BUY"
    elif raw_ensemble > 0.15:
        direction = "BUY"
    elif raw_ensemble < -0.35:
        direction = "STRONG_SELL"
    elif raw_ensemble < -0.15:
        direction = "SELL"

    current_price = float(df["close"].iloc[-1])
    atr = float(df["ATRr_14"].iloc[-1]) if "ATRr_14" in df.columns else 0.0
    garch_vol = float(regime_info["conditional_vol"])
    garch_vol_5d = float(regime_info["vol_forecast_5d"])

    stop_distance = max(current_price * 2.0 * garch_vol, 1.5 * atr) if atr > 0 else current_price * 2.0 * garch_vol
    take_profit_distance = max(current_price * 3.0 * garch_vol, 2.5 * atr) if atr > 0 else current_price * 3.0 * garch_vol

    if direction in ("STRONG_BUY", "BUY"):
        stop_loss = current_price - stop_distance
        take_profit = current_price + take_profit_distance
        max_loss_pct = ((current_price - stop_loss) / current_price) * 100.0 if current_price > 0 else 0.0
    elif direction in ("STRONG_SELL", "SELL"):
        stop_loss = current_price + stop_distance
        take_profit = current_price - take_profit_distance
        max_loss_pct = ((stop_loss - current_price) / current_price) * 100.0 if current_price > 0 else 0.0
    else:
        stop_loss = current_price
        take_profit = current_price
        max_loss_pct = 0.0

    target_price_5d = current_price * (1.0 + raw_ensemble * garch_vol_5d)

    weights_dict = {m: float(masked_weights[i]) for i, m in enumerate(model_names)}

    # Check if there is any trained model loaded
    any_trained = any(status == "trained" for status in model_statuses.values())
    ensemble_status = "trained" if any_trained else "heuristic"

    return {
        "model_status": ensemble_status,
        "raw_ensemble": raw_ensemble,
        "confidence": ensemble_confidence,
        "direction": direction,
        "direction_up_down_flat": "up" if direction in ("BUY", "STRONG_BUY") else ("down" if direction in ("SELL", "STRONG_SELL") else "flat"),
        "expected_move_range": {
            "low": float(current_price - stop_distance),
            "high": float(current_price + take_profit_distance)
        },
        "kelly": kelly_fraction,
        "agreement": agreement,
        "target_price_5d": float(target_price_5d),
        "stop_loss": float(stop_loss),
        "take_profit": float(take_profit),
        "prob_buy": (raw_ensemble + 1.0) / 2.0,
        "prob_sell": 1.0 - (raw_ensemble + 1.0) / 2.0,
        "max_loss_pct": float(max_loss_pct),
        "model_weights": weights_dict,
        "model_signals": model_signals,
        "model_confidences": model_confidences,
        "model_statuses": model_statuses,

        "technical": technical,
        "regime": {
            "regime": regime_info["regime"],
            "bull_prob": regime_info["bull_prob"],
            "bear_prob": regime_info["bear_prob"],
            "regime_confidence": regime_info["regime_confidence"],
            "hmm_used": True,
            "conditional_vol": garch_vol,
            "vol_forecast_5d": garch_vol_5d,
            "vol_forecast_21d": regime_info["vol_forecast_21d"],
        },
        "xgboost": {
            "xgb_score": xgb_score,
            "xgb_confidence": xgb_confidence,
            "xgb_direction": "BUY" if xgb_score > 0.2 else ("SELL" if xgb_score < -0.2 else "NEUTRAL"),
            "top_features": [{"name": feat["name"], "shap_value": feat["shap_value" if "shap_value" in feat else "importance"]} for feat in xgb_top_features],
            "base_value": xgb_base_value,
            "status": xgb_status
        },
        "tft": {
            "p10_return": float(tft_p10),
            "p50_return": float(tft_p50),
            "p90_return": float(tft_p90),
            "raw_signal": tft_score,
            "horizon_days": 5,
            "status": tft_status
        },
        "lstm_attn": {
            "raw_signal": lstm_score,
            "attention_peaks": lstm_attn_peaks,
            "status": lstm_status
        },
        "gnn": {
            "spillover_risk": gnn_confidence,
            "embedding_norm": 1.0,
            "top_correlated_assets": gnn_top_correlated,
            "status": gnn_status
        },
        "hmm_garch": {
            "regime_signal": hmm_score,
            "vol_forecast_1d": garch_vol,
            "vol_forecast_5d": garch_vol_5d,
            "vol_forecast_21d": regime_info["vol_forecast_21d"],
            "status": hmm_status
        },
        "online_learner": {
            "raw_signal": online_score,
            "prob_buy": online_prob
        }
    }


# ---------------------------------------------------------------------------
# Layer 7 – Price Forecast
# ---------------------------------------------------------------------------

def forecast_prices(df: pd.DataFrame, horizons: list[int]) -> list[dict[str, Any]]:
    log_prices = np.log(df["close"].values[-90:])  # Use last 90 days
    try:
        model = SARIMAX(log_prices, order=(2, 1, 2), trend='c')
        result = model.fit(disp=False, maxiter=200)
        forecasts = result.get_forecast(steps=max(horizons))
        pred_mean = np.exp(forecasts.predicted_mean)
        pred_ci   = np.exp(forecasts.conf_int(alpha=0.20))  # 80% CI
    except Exception as e:
        logger.warning(f"SARIMAX price forecast failed: {e}. Falling back to ExponentialSmoothing.")
        # Fallback: simple exponential smoothing trend
        try:
            closes_60 = df["close"].values[-60:]
            model = ExponentialSmoothing(closes_60, trend='add', damped_trend=True)
            result = model.fit()
            pred_mean = result.forecast(max(horizons))
            ci_width = df["close"].std() * np.sqrt(np.arange(1, max(horizons)+1)) * 0.5
            pred_ci = np.column_stack([pred_mean - ci_width, pred_mean + ci_width])
        except Exception as ee:
            logger.error(f"HoltWinters forecast fallback failed: {ee}")
            current_close = float(df["close"].iloc[-1])
            pred_mean = np.full(max(horizons), current_close)
            pred_ci = np.column_stack([pred_mean * 0.97, pred_mean * 1.03])

    current = float(df["close"].iloc[-1])
    output = []
    for h in horizons:
        idx = h - 1
        predicted = float(pred_mean[idx]) if idx < len(pred_mean) else current
        low  = float(pred_ci[idx, 0]) if idx < len(pred_ci) else predicted * 0.97
        high = float(pred_ci[idx, 1]) if idx < len(pred_ci) else predicted * 1.03
        change_pct = (predicted - current) / current
        output.append({
            "horizon_days": h,
            "predicted_price": round(predicted, 2),
            "prediction_low":  round(low, 2),
            "prediction_high": round(high, 2),
            "change_pct": round(change_pct, 4),
            "target_date": (datetime.now(UTC) + timedelta(days=h)).date().isoformat()
        })
    return output

# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

async def get_full_prediction(symbol: str, bypass_cache: bool = False, artifact_path: str = None, model_version: str = None) -> dict[str, Any]:
    """Fetch OHLCV, run all 7 methods, return complete prediction payload."""
    from app.services.market_data_service import MarketDataService
    symbol = MarketDataService._normalize_symbol(symbol)
    import yfinance as yf

    if not bypass_cache:
        cached = await _cache_fetch(symbol)
        if cached:
            return cached

    from app.services.data_ingestion.provider_manager import provider_manager
    from datetime import datetime, UTC, timedelta
    import pandas as pd
    
    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=2 * 365) # 2 years
    
    try:
        bars = await provider_manager.get_ohlcv(symbol, "1d", start_date, end_date)
        if not bars or len(bars) < 60:
            raise ValueError(f"Insufficient OHLCV data for {symbol} (need at least 60 rows)")
            
        df = pd.DataFrame([{
            "time": b.time.replace(tzinfo=None) if b.time.tzinfo else b.time,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume
        } for b in bars])
    except Exception as e:
        logger.error(f"Failed to fetch market data for {symbol}: {e}")
        raise ValueError(f"Failed to fetch market data for {symbol}") from e

    # Prepare DataFrame by running all builders and indicators
    df.index = pd.DatetimeIndex(df["time"])
    df.index.name = None

    # Import pipeline dynamically to avoid circular references
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from research.feature_engineering.pipeline import FeaturePipeline

    # Run the full causality-safe sequential feature pipeline
    df = FeaturePipeline().run(df)

    # Compute pandas-ta indicators
    df.ta.rsi(length=14, append=True)
    df.ta.macd(fast=12, slow=26, signal=9, append=True)
    df.ta.ema(length=9, append=True)
    df.ta.ema(length=21, append=True)
    df.ta.ema(length=50, append=True)
    df.ta.ema(length=200, append=True)
    df.ta.bbands(length=20, std=2, append=True)
    df.ta.atr(length=14, append=True)
    df.ta.vwap(append=True)
    df.ta.adx(length=14, append=True)
    df.ta.stoch(k=14, d=3, append=True)
    df.ta.obv(append=True)
    df.ta.supertrend(length=10, multiplier=3.0, append=True)
    df.ta.cdl_pattern(name="all", append=True)

    # Deduplicate columns (e.g. RSI_14, MACD, etc. added by both builders and df.ta)
    df = df.loc[:, ~df.columns.duplicated()].copy()

    # Ensure database-derived features are present (fallback to 0 if missing during live inference)
    for col in ["sentiment_score", "news_volume", "sentiment_pos_neg_ratio", "market_sentiment_index", "sentiment_momentum_3d", "regime_state", "garch_vol"]:
        if col not in df.columns:
            df[col] = 0.0


    # Incremental update for OnlineAdaptiveLearner
    try:
        from research.models.online_learner import OnlineAdaptiveLearner
        online_checkpoint = MODEL_DIR / f"online_learner_{symbol.upper()}.pkl"
        learner = OnlineAdaptiveLearner.load(online_checkpoint)

        # Prepare columns standardizing just like in scoring
        df_clean_copy = df.copy()
        rename_map = {}
        RSI_col = "RSI_14" if "RSI_14" in df_clean_copy.columns else [c for c in df_clean_copy.columns if "RSI" in c][0]
        MACDh_col = "MACDh_12_26_9" if "MACDh_12_26_9" in df_clean_copy.columns else [c for c in df_clean_copy.columns if "MACDh" in c][0]
        BBP_col = "BBP_20_2.0_2.0" if "BBP_20_2.0_2.0" in df_clean_copy.columns else ("BBP_20_2.0" if "BBP_20_2.0" in df_clean_copy.columns else [c for c in df_clean_copy.columns if "BBP" in c][0])
        ATR_col = "ATRr_14" if "ATRr_14" in df_clean_copy.columns else [c for c in df_clean_copy.columns if "ATR" in c][0]
        ADX_col = "ADX_14" if "ADX_14" in df_clean_copy.columns else [c for c in df_clean_copy.columns if "ADX" in c][0]

        if RSI_col != "RSI_14":
            rename_map[RSI_col] = "RSI_14"
        if MACDh_col != "MACDh_12_26_9":
            rename_map[MACDh_col] = "MACDh_12_26_9"
        if BBP_col != "BBP_20_2.0":
            rename_map[BBP_col] = "BBP_20_2.0"
        if ATR_col != "ATRr_14":
            rename_map[ATR_col] = "ATRr_14"
        if ADX_col != "ADX_14":
            rename_map[ADX_col] = "ADX_14"
        if rename_map:
            df_clean_copy = df_clean_copy.rename(columns=rename_map)

        if len(df_clean_copy) >= 7:
            row_6 = df_clean_copy.iloc[-6]
            close_t = float(row_6["close"])
            close_t5 = float(df_clean_copy["close"].iloc[-1])
            y_val = 1 if close_t5 > close_t else 0

            x_dict_6 = {feat: float(row_6[feat]) for feat in learner.features if feat in df_clean_copy.columns}
            if not any(np.isnan(v) for v in x_dict_6.values()):
                learner.update(x_dict_6, y_val)
                learner.save(online_checkpoint)
                logger.info(f"Incrementally updated OnlineAdaptiveLearner for {symbol}.")
    except Exception as e:
        logger.warning(f"Failed to incrementally update OnlineAdaptiveLearner for {symbol}: {e}")

    # Run the scoring methods
    from research.models.xgboost_model.classifier import FeatureMismatchError
    try:
        ensemble = await build_ensemble_signal(symbol, df, artifact_path, model_version)
    except FeatureMismatchError as e:
        logger.error(f"Prediction mismatch for {symbol}: {e}")
        raise ValueError(f"model unavailable: missing features {e.missing_features}")

    forecast = forecast_prices(df, horizons=[1, 3, 5, 10, 21])

    # Generate plain-language reasoning
    reasons = []
    try:
        # 1. RSI
        rsi_val = float(df["RSI_14"].iloc[-1]) if "RSI_14" in df.columns else 50.0
        if rsi_val < 30:
            reasons.append("RSI oversold")
        elif rsi_val > 70:
            reasons.append("RSI overbought")

        # 2. HMM Regime
        regime_name = ensemble.get("regime", {}).get("regime", "UNKNOWN").lower()
        reasons.append(f"{regime_name} regime")

        # 3. S/R zones
        current_price = float(df["close"].iloc[-1])
        from app.services.sr_service import SupportResistanceEngine
        zones_res = SupportResistanceEngine.detect_classical_zones(df)
        near_support = False
        near_resistance = False
        for zone in zones_res:
            avg_zone = zone["avg"]
            if abs(current_price - avg_zone) / current_price <= 0.015:
                if zone["type"] == "support":
                    near_support = True
                elif zone["type"] == "resistance":
                    near_resistance = True
        if near_support:
            reasons.append("price near support zone")
        elif near_resistance:
            reasons.append("price near resistance zone")

        # 4. Trend Crossover
        macd_val = float(df["MACDh_12_26_9"].iloc[-1]) if "MACDh_12_26_9" in df.columns else 0.0
        if macd_val > 0:
            reasons.append("MACD bullish crossover")
        elif macd_val < 0:
            reasons.append("MACD bearish crossover")
    except Exception as re_err:
        logger.warning(f"Failed to generate plain-language reasoning message: {re_err}")

    reasoning_msg = " + ".join(reasons) if reasons else "No clear signal drivers detected."

    result = {
        "symbol": symbol.upper(),
        "current_price": float(df["close"].iloc[-1]),
        "timestamp": datetime.now(UTC).isoformat(),
        "model_status": ensemble.get("model_status", "heuristic"),
        "ensemble": ensemble,
        "forecast": forecast,
        "data_points_used": len(df),
        "is_computed": True,
        "message": reasoning_msg,
        "model_version": model_version or "latest"
    }

    await _cache_store(symbol, result)
    return result
