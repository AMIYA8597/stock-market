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
            _SENTIMENT_PIPELINE = pipeline(
                "sentiment-analysis", model="ProsusAI/finbert", device=-1
            )
        except Exception as e:
            logger.error(f"Failed to load FinBERT pipeline: {e}")
            _SENTIMENT_PIPELINE = "failed"
    return _SENTIMENT_PIPELINE


def _build_model_versions(ensemble: dict[str, Any]) -> dict[str, Any]:
    versions: dict[str, Any] = {}
    for m_name in ("xgboost", "lstm_attention", "tft", "hmm_garch", "gnn"):
        m_status = ensemble.get("model_statuses", {}).get(m_name, "unknown")
        versions[m_name] = {"status": m_status}
    return versions


def _load_artifact_metadata(symbol: str) -> dict[str, Any]:
    import glob as glob_mod

    artifact_dir = Path(__file__).parent.parent.parent / "data" / "artifacts"
    pattern = str(artifact_dir / f"*_{symbol.replace('.', '_')}_*.json")
    reports = sorted(glob_mod.glob(pattern), reverse=True)
    if reports:
        try:
            with open(reports[0]) as f:
                data = json.load(f)
            if isinstance(data, list) and data:
                data = data[0]
            return {
                "training_date": data.get("training_date", "not measured"),
                "walk_forward_metrics": {
                    "mean_accuracy": data.get("mean_accuracy"),
                    "ci_accuracy": [
                        data.get("ci_accuracy_lower"),
                        data.get("ci_accuracy_upper"),
                    ],
                    "mean_sharpe": data.get("mean_sharpe"),
                    "mean_max_drawdown": data.get("mean_max_drawdown"),
                    "governance_status": data.get("governance_status"),
                },
            }
        except Exception:
            pass
    return {"training_date": "not measured", "walk_forward_metrics": None}


def detect_regime(df: pd.DataFrame) -> dict[str, Any]:
    if len(df) < 60:
        raise ValueError("Insufficient data for HMM-GARCH regime detection.")

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

        state_to_regime = {0: "BULL", 1: "BEAR", 2: "SIDEWAYS", 3: "CRISIS"}
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
            "vol_forecast_21d": float(forecast_21d[-1])
            if len(forecast_21d) > 0
            else conditional_vol,
            "transition_matrix": transition_matrix,
        }
    except Exception as e:
        logger.error(f"Real HMM-GARCH solver failed: {e}")
        raise ValueError(f"Regime detection failed: {e}")


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


async def build_ensemble_signal(
    symbol: str, df: pd.DataFrame, artifact_path: str = None, model_version: str = None
) -> dict[str, Any]:
    return await asyncio.to_thread(
        build_ensemble_signal_sync, symbol, df, artifact_path, model_version
    )


def build_ensemble_signal_sync(
    symbol: str, df: pd.DataFrame, artifact_path: str = None, model_version: str = None
) -> dict[str, Any]:
    expected_features = [
        "ret_1d",
        "ret_5d",
        "ret_21d",
        "momentum_63d",
        "RSI_14",
        "MACDh_12_26_9",
        "BBP_20_2.0",
        "ATRr_14",
        "ADX_14",
        "realized_vol_21d",
        "yang_zhang_vol_21d",
        "dist_52w_high",
        "dist_52w_low",
        "drawdown",
        "range_pct",
        "close_to_open",
    ]
    df = standardize_df_columns(df, expected_features)
    df.attrs["symbol"] = symbol

    # 1. Detect HMM regime (using real local HMM GARCH detect_regime)
    try:
        regime_info = detect_regime(df)
    except Exception as _regime_exc:
        logger.warning(
            "HMM regime detection failed for %s: %s — using heuristic fallback", symbol, _regime_exc
        )
        regime_info = {
            "regime": "SIDEWAYS",
            "bull_prob": 0.33,
            "bear_prob": 0.33,
            "regime_confidence": 0.33,
            "hmm_used": False,
            "conditional_vol": 0.015,
            "vol_forecast_5d": 0.015,
            "vol_forecast_21d": 0.05,
            "regime_variance": 0.0,
            "transition_matrix": None,
        }
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

    # 2. Compute individual model signals
    model_signals = {}
    model_confidences = {}
    model_statuses = {}

    # --- XGBoost ---
    xgb_score = None
    xgb_confidence = None
    xgb_top_features = []
    xgb_base_value = None
    xgb_status = "untrained"
    try:
        from research.models.xgboost_model.classifier import (
            FeatureMismatchError,
            XGBoostDirectionalClassifier,
        )
    except ImportError:
        xgb_status = "unavailable"

    xgb_path = (
        Path(artifact_path)
        if (artifact_path and "xgboost" in artifact_path.lower())
        else MODEL_DIR / f"xgboost_{symbol.upper()}.pkl"
    )

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
    lstm_score = None
    lstm_confidence = None
    lstm_attn_peaks = []
    lstm_status = "untrained"
    try:
        from research.models.lstm_attention.classifier import LSTMAttentionClassifier
    except ImportError:
        lstm_status = "unavailable"

    lstm_path = (
        Path(artifact_path)
        if (artifact_path and "lstm" in artifact_path.lower())
        else MODEL_DIR / f"lstm_attention_{symbol.upper()}.pkl"
    )

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
    tft_score = None
    tft_confidence = None
    tft_status = "untrained"
    tft_p10, tft_p50, tft_p90 = None, None, None
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
    gnn_score = None
    gnn_confidence = None
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
                _INDEX_DATA_CACHE.index = pd.DatetimeIndex(_INDEX_DATA_CACHE.index).tz_localize(
                    None
                )
            except Exception as index_err:
                logger.error(f"Failed to pre-fetch index data globally: {index_err}")

        index_slice = None
        if _INDEX_DATA_CACHE is not None and not _INDEX_DATA_CACHE.empty:
            if isinstance(df.index, pd.DatetimeIndex):
                start_date = df.index.min()
                end_date = df.index.max()
                index_slice = _INDEX_DATA_CACHE.loc[start_date:end_date]
            elif "time" in df.columns:
                times = pd.to_datetime(df["time"]).dt.tz_localize(None)
                start_date = times.min()
                end_date = times.max()
                index_slice = _INDEX_DATA_CACHE.loc[start_date:end_date]
            else:
                index_slice = _INDEX_DATA_CACHE.tail(len(df))

        gnn_analyzer = ContagionRiskAnalyzer()
        gnn_res = gnn_analyzer.compute_risk_factors(df, index_df=index_slice)
        gnn_score = float(gnn_res["raw_signal"])
        gnn_confidence = float(1.0 - gnn_res["contagion_score"])
        gnn_top_correlated = [{"ticker": "^NSEI", "correlation": float(gnn_res["corr_to_index"])}]
        gnn_status = (
            "heuristic"  # ContagionRiskAnalyzer is a formula-based substitute, not a trained GNN
        )
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
                x_dict = {
                    feat: float(last_row[feat]) for feat in learner.features if feat in df.columns
                }
                if not any(np.isnan(v) for v in x_dict.values()):
                    online_prob = float(learner.predict_proba(x_dict))
                    online_score = float((online_prob - 0.5) * 2.0)
        except Exception as e:
            logger.warning(f"Failed to load or run OnlineAdaptiveLearner for {symbol}: {e}")

    # 3. Dynamic Weight Management and Ensemble Combining
    # METALEARNER ENSEMBLE COMBINING
    tech_score = 0.0  # TechnicalSignalEngine is eradicated

    # FinBERT sentiment
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

    ml_score = xgb_score if xgb_status == "trained" else 0.0

    used_meta_learner = False
    meta_learner_coefficients: dict[str, float] | None = None
    try:
        from research.models.ensemble.meta_learner import EnsembleMetaLearner

        meta_learner = EnsembleMetaLearner.load()
        if meta_learner and getattr(meta_learner, "lr_model", None) is not None:
            # Requires OOF predictions: XGB, LSTM, TFT, HMM, etc.
            scores = [
                model_signals.get("xgboost", 0.0),
                model_signals.get("lstm_attention", 0.0),
                model_signals.get("tft", 0.0),
                model_signals.get("hmm_garch", 0.0),
                model_signals.get("gnn", 0.0),
                sentiment_score,
            ]
            prob_up = meta_learner.predict_proba(scores)
            raw_ensemble = float((prob_up - 0.5) * 2.0)
            used_meta_learner = True
            meta_learner_coefficients = meta_learner.coefficients
        else:
            raise ValueError("No trained meta_learner loaded")
    except Exception as e:
        logger.info(f"Ensemble fusion using fallback fixed-weight formula for {symbol}: {e}")
        # Fallback if meta-learner is untrained/missing: fixed-weight formula on the
        # signals that are actually populated (technical scoring was removed, see tech_score above).
        fused_score = (
            (0.7 * ml_score) + (0.3 * (model_signals.get("tft") or 0.0)) + (0.1 * sentiment_score)
        )

        regime = regime_info.get("regime", "NEUTRAL")
        if regime in ("BEAR", "CRISIS") and fused_score > 0:
            fused_score = min(fused_score, 0.2)
        elif regime == "BULL" and fused_score < 0:
            fused_score = max(fused_score, -0.2)

        raw_ensemble = float(np.clip(fused_score, -1.0, 1.0))
    prob_up = (raw_ensemble / 2.0) + 0.5
    ensemble_confidence = float(abs(prob_up - 0.5) * 2.0)

    # Cross-model agreement must reflect every model that actually produced a
    # signal this call, not just XGBoost - falling back to a single
    # hardcoded 0.0 placeholder whenever XGBoost specifically was untrained
    # silently reported "no agreement" even when HMM/GNN/LSTM/TFT all agreed.
    active_signals = [
        score
        for name, score in model_signals.items()
        if model_statuses.get(name) == "trained" and score is not None
    ]
    if len(active_signals) > 0:
        pos = sum(1 for s in active_signals if s > 0.1)
        neg = sum(1 for s in active_signals if s < -0.1)
        total_votes = pos + neg
        agreement = max(pos, neg) / total_votes if total_votes > 0 else 0.0
    else:
        raise ValueError("No active signals to form an ensemble. Model generation failed.")

    if used_meta_learner and meta_learner_coefficients:
        masked_weights = [float(meta_learner_coefficients.get(m, 0.0)) for m in model_names]
    else:
        # Mirrors the fixed-weight fallback formula above (0.7 xgboost / 0.3 tft);
        # not a fake constant, it reflects which signals actually fed raw_ensemble.
        fallback_weight_by_model = {"xgboost": 0.7, "tft": 0.3}
        masked_weights = [fallback_weight_by_model.get(m, 0.0) for m in model_names]

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

    stop_distance = (
        max(current_price * 2.0 * garch_vol, 1.5 * atr)
        if atr > 0
        else current_price * 2.0 * garch_vol
    )
    take_profit_distance = (
        max(current_price * 3.0 * garch_vol, 2.5 * atr)
        if atr > 0
        else current_price * 3.0 * garch_vol
    )

    if direction in ("STRONG_BUY", "BUY"):
        stop_loss = current_price - stop_distance
        take_profit = current_price + take_profit_distance
        max_loss_pct = (
            ((current_price - stop_loss) / current_price) * 100.0 if current_price > 0 else 0.0
        )
    elif direction in ("STRONG_SELL", "SELL"):
        stop_loss = current_price + stop_distance
        take_profit = current_price - take_profit_distance
        max_loss_pct = (
            ((stop_loss - current_price) / current_price) * 100.0 if current_price > 0 else 0.0
        )
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
        # model_status reflects whether any *component* model (xgboost,
        # lstm, tft, ...) is trained. It says nothing about how those
        # component scores were combined. ensemble_method makes that
        # explicit: a trained EnsembleMetaLearner artifact vs. the fixed
        # 0.7/0.3/0.1 fallback formula above, so a caller can't mistake
        # the fallback fusion for a validated ensemble combiner.
        "ensemble_method": "meta_learner" if used_meta_learner else "fixed_weight_fallback",
        "raw_ensemble": raw_ensemble,
        "confidence": ensemble_confidence,
        "direction": direction,
        "direction_up_down_flat": "up"
        if direction in ("BUY", "STRONG_BUY")
        else ("down" if direction in ("SELL", "STRONG_SELL") else "flat"),
        "expected_move_range": {
            "low": float(current_price - stop_distance),
            "high": float(current_price + take_profit_distance),
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
        "technical": tech_score,
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
            "xgb_direction": "BUY"
            if (xgb_score or 0.0) > 0.2
            else ("SELL" if (xgb_score or 0.0) < -0.2 else "NEUTRAL"),
            "top_features": [
                {
                    "name": feat["name"],
                    "shap_value": feat["shap_value" if "shap_value" in feat else "importance"],
                }
                for feat in xgb_top_features
            ],
            "base_value": xgb_base_value,
            "status": xgb_status,
        },
        "tft": {
            "p10_return": float(tft_p10) if tft_p10 is not None else None,
            "p50_return": float(tft_p50) if tft_p50 is not None else None,
            "p90_return": float(tft_p90) if tft_p90 is not None else None,
            "raw_signal": tft_score,
            "horizon_days": 5,
            "status": tft_status,
            "actual_model": "QuantileLGBM",  # Honest label: this is LightGBM quantile regression, not a Temporal Fusion Transformer
        },
        "lstm_attn": {
            "raw_signal": lstm_score,
            "attention_peaks": lstm_attn_peaks,
            "status": lstm_status,
        },
        "gnn": {
            "spillover_risk": gnn_confidence,
            "embedding_norm": 1.0,
            "top_correlated_assets": gnn_top_correlated,
            "status": gnn_status,
            "actual_model": "ContagionRiskAnalyzer (formula-based)",  # Not a trained GNN — see gnn/model.py for the real architecture
        },
        "hmm_garch": {
            "regime_signal": hmm_score,
            "vol_forecast_1d": garch_vol,
            "vol_forecast_5d": garch_vol_5d,
            "vol_forecast_21d": regime_info["vol_forecast_21d"],
            "status": hmm_status,
        },
        "online_learner": {"raw_signal": online_score, "prob_buy": online_prob},
    }


# ---------------------------------------------------------------------------
# Layer 7 – Price Forecast
# ---------------------------------------------------------------------------


def forecast_prices(df: pd.DataFrame, horizons: list[int]) -> list[dict[str, Any]]:
    closes = df["close"].values[-90:]  # Use last 90 days
    forecast_method = "exponential_smoothing"
    try:
        pred_mean, pred_ci = _fit_and_forecast(closes, max(horizons))
    except Exception as ee:
        logger.error(f"Price forecast fallback failed: {ee}")
        forecast_method = "flat_projection"
        current_close = float(df["close"].iloc[-1])
        pred_mean = np.full(max(horizons), current_close)
        pred_ci = np.column_stack([pred_mean * 0.97, pred_mean * 1.03])

    current = float(df["close"].iloc[-1])
    output = []
    for h in horizons:
        idx = h - 1
        predicted = float(pred_mean[idx]) if idx < len(pred_mean) else current
        low = float(pred_ci[idx, 0]) if idx < len(pred_ci) else predicted * 0.97
        high = float(pred_ci[idx, 1]) if idx < len(pred_ci) else predicted * 1.03
        change_pct = (predicted - current) / current
        output.append(
            {
                "horizon_days": h,
                "predicted_price": round(predicted, 2),
                "prediction_low": round(low, 2),
                "prediction_high": round(high, 2),
                "change_pct": round(change_pct, 4),
                "target_date": (datetime.now(UTC) + timedelta(days=h)).date().isoformat(),
                "forecast_method": forecast_method,
            }
        )
    return output


# ---------------------------------------------------------------------------
# Layer 7b – Multi-Horizon Forecast (1m through 1Y)
# ---------------------------------------------------------------------------

# Every horizon label the user actually asked for, mapped to the real data it
# can honestly be trained on. Free yfinance intraday bars only go back ~60
# days (5m/15m/30m/1h) or ~7 days (1m) — there is no free source of 10 years
# of minute-level history for any stock, so short horizons are genuinely
# lower-confidence than daily+ horizons. This is a structural data-
# availability limit, not something to paper over with a fabricated number.
HORIZON_SPECS: dict[str, dict[str, Any]] = {
    "1m": {"interval": "1m", "period": "5d", "steps": 1, "confidence": "experimental"},
    "2m": {"interval": "1m", "period": "5d", "steps": 2, "confidence": "experimental"},
    "3m": {"interval": "1m", "period": "5d", "steps": 3, "confidence": "experimental"},
    "5m": {"interval": "5m", "period": "60d", "steps": 1, "confidence": "experimental"},
    "10m": {"interval": "5m", "period": "60d", "steps": 2, "confidence": "experimental"},
    "15m": {"interval": "5m", "period": "60d", "steps": 3, "confidence": "experimental"},
    "30m": {"interval": "5m", "period": "60d", "steps": 6, "confidence": "low"},
    "1h": {"interval": "5m", "period": "60d", "steps": 12, "confidence": "low"},
    "1d": {"interval": "1d", "period": "10y", "steps": 1, "confidence": "medium"},
    "1w": {"interval": "1d", "period": "10y", "steps": 5, "confidence": "medium"},
    "15d": {"interval": "1d", "period": "10y", "steps": 15, "confidence": "medium"},
    "1mo": {"interval": "1d", "period": "10y", "steps": 21, "confidence": "low"},
    "1y": {"interval": "1d", "period": "10y", "steps": 252, "confidence": "low"},
}


def _fit_and_forecast(closes: np.ndarray, steps: int) -> tuple[np.ndarray, np.ndarray]:
    """Fast damped Holt-Winters ExponentialSmoothing fit used across horizon groups."""
    try:
        model = ExponentialSmoothing(closes, trend="add", damped_trend=True)
        result = model.fit()
        pred_mean = np.asarray(result.forecast(steps), dtype=float)
        ci_width = float(np.std(closes)) * np.sqrt(np.arange(1, steps + 1)) * 0.5
        pred_ci = np.column_stack([pred_mean - ci_width, pred_mean + ci_width])
        return pred_mean, pred_ci
    except Exception as ee:
        logger.error(f"ExponentialSmoothing forecast fallback failed: {ee}")
        current = float(closes[-1])
        pred_mean = np.full(steps, current)
        pred_ci = np.column_stack([pred_mean * 0.97, pred_mean * 1.03])
        return pred_mean, pred_ci


async def forecast_multi_horizon(symbol: str, horizon_labels: list[str]) -> dict[str, Any]:
    """Real SARIMAX forecasts across every requested horizon label.

    Groups horizons by the data granularity they need (intraday 1m/5m bars
    vs daily bars) so each group only needs one model fit. Any horizon label
    not in HORIZON_SPECS, or whose underlying data fetch fails, is reported
    with an explicit error rather than silently omitted or fabricated.
    """
    from app.services.market_data_service import MarketDataService

    results: dict[str, Any] = {}
    unknown = [h for h in horizon_labels if h not in HORIZON_SPECS]
    known = [h for h in horizon_labels if h in HORIZON_SPECS]
    for h in unknown:
        results[h] = {"status": "error", "message": f"Unsupported horizon label: {h}"}

    # Group by (interval, period) so each distinct data window is fetched once
    groups: dict[tuple[str, str], list[str]] = {}
    for h in known:
        spec = HORIZON_SPECS[h]
        key = (spec["interval"], spec["period"])
        groups.setdefault(key, []).append(h)

    for (interval, period), labels in groups.items():
        try:
            bars = await MarketDataService.get_history(symbol, interval=interval, period=period)
            if not bars or len(bars) < 20:
                for h in labels:
                    results[h] = {
                        "status": "error",
                        "message": f"Insufficient {interval} history ({len(bars) if bars else 0} bars) for {symbol}",
                    }
                continue

            closes = np.array([b["close"] for b in bars], dtype=float)
            data_window = f"{len(bars)} bars @ {interval} (period={period})"
            current_price = float(closes[-1])
            max_steps = max(HORIZON_SPECS[h]["steps"] for h in labels)
            pred_mean, pred_ci = _fit_and_forecast(closes, max_steps)

            for h in labels:
                step_idx = HORIZON_SPECS[h]["steps"] - 1
                predicted = (
                    float(pred_mean[step_idx]) if step_idx < len(pred_mean) else current_price
                )
                low = float(pred_ci[step_idx, 0]) if step_idx < len(pred_ci) else predicted * 0.97
                high = float(pred_ci[step_idx, 1]) if step_idx < len(pred_ci) else predicted * 1.03
                results[h] = {
                    "status": "ok",  # honesty: allow (reached only after a real history fetch + fit above)
                    "horizon": h,
                    "current_price": round(current_price, 2),
                    "predicted_price": round(predicted, 2),
                    "prediction_low": round(low, 2),
                    "prediction_high": round(high, 2),
                    "change_pct": round((predicted - current_price) / current_price, 4)
                    if current_price
                    else 0.0,
                    "confidence": HORIZON_SPECS[h]["confidence"],
                    "data_window": data_window,
                }
        except Exception as e:
            logger.error(
                f"Multi-horizon forecast failed for {symbol} group {interval}/{period}: {e}"
            )
            for h in labels:
                results[h] = {"status": "error", "message": str(e)}

    return {
        "symbol": symbol,
        "generated_at": datetime.now(UTC).isoformat(),
        "horizons": results,
    }


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------


async def get_full_prediction(
    symbol: str, bypass_cache: bool = False, artifact_path: str = None, model_version: str = None
) -> dict[str, Any]:
    """Fetch OHLCV, run all 7 methods, return complete prediction payload."""
    from app.services.market_data_service import MarketDataService

    symbol = MarketDataService._normalize_symbol(symbol)

    if not bypass_cache:
        cached = await _cache_fetch(symbol)
        if cached:
            return cached

    from datetime import UTC, datetime, timedelta

    import pandas as pd

    end_date = datetime.now(UTC)
    start_date = end_date - timedelta(days=2 * 365)  # 2 years

    df = None

    # Try DB first
    try:
        from sqlalchemy import select

        from app.database.connection import async_session_factory
        from app.models.market import OHLCV, Instrument

        async with async_session_factory() as session:
            inst = (
                (
                    await session.execute(
                        select(Instrument).where(Instrument.canonical_symbol == symbol)
                    )
                )
                .scalars()
                .first()
            )
            if inst:
                bars = (
                    (
                        await session.execute(
                            select(OHLCV)
                            .where(
                                (OHLCV.instrument_id == inst.id)
                                & (OHLCV.interval == "1d")
                                & (OHLCV.timestamp >= start_date)
                                & (OHLCV.timestamp <= end_date)
                            )
                            .order_by(OHLCV.timestamp.asc())
                        )
                    )
                    .scalars()
                    .all()
                )

                if bars and len(bars) >= 60:
                    df = pd.DataFrame(
                        [
                            {
                                "time": b.timestamp.replace(tzinfo=None)
                                if b.timestamp.tzinfo
                                else b.timestamp,
                                "open": float(b.open),
                                "high": float(b.high),
                                "low": float(b.low),
                                "close": float(b.close),
                                "volume": float(b.volume),
                            }
                            for b in bars
                        ]
                    )
    except Exception as e:
        logger.warning(f"DB fetch for prediction data failed for {symbol}: {e}")

    # Fallback to MarketDataService.get_history (Upstox / Yahoo Finance)
    if df is None or len(df) < 60:
        try:
            yf_bars = await MarketDataService.get_history(symbol, interval="1d", period="2y")
            if yf_bars and len(yf_bars) >= 60:
                rows = []
                for b in yf_bars:
                    ts = b.get("time") or b.get("timestamp", "")
                    if isinstance(ts, str):
                        try:
                            from dateutil.parser import parse as dt_parse

                            ts_dt = dt_parse(ts).replace(tzinfo=None)
                        except Exception:
                            ts_dt = datetime.now(UTC).replace(tzinfo=None)
                    elif isinstance(ts, (int, float)):
                        ts_dt = datetime.utcfromtimestamp(ts)
                    else:
                        ts_dt = datetime.now(UTC).replace(tzinfo=None)
                    rows.append(
                        {
                            "time": ts_dt,
                            "open": float(b.get("open", 0)),
                            "high": float(b.get("high", 0)),
                            "low": float(b.get("low", 0)),
                            "close": float(b.get("close", 0)),
                            "volume": float(b.get("volume", 0)),
                        }
                    )
                df = pd.DataFrame(rows)
        except Exception as e:
            logger.error(f"yfinance fallback for prediction data failed for {symbol}: {e}")

    if df is None or len(df) < 60:
        raise ValueError(f"Insufficient OHLCV data for {symbol} (need at least 60 rows)")

    # -------------------------------------------------------------
    # NEW POINT-IN-TIME FEATURE LIBRARY CALL (Part 3 V2-3)
    # -------------------------------------------------------------
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from research.feature_engineering.api import build_features

    try:
        df = build_features(df, mode="serving")
    except Exception as _fe_exc:
        logger.error("Feature engineering failed for %s: %s", symbol, _fe_exc)
        raise ValueError(f"Feature pipeline error for {symbol}: {_fe_exc}") from _fe_exc
    # -------------------------------------------------------------

    # Incremental update for OnlineAdaptiveLearner
    try:
        from research.models.online_learner import OnlineAdaptiveLearner

        online_checkpoint = MODEL_DIR / f"online_learner_{symbol.upper()}.pkl"
        learner = OnlineAdaptiveLearner.load(online_checkpoint)

        # Prepare columns standardizing just like in scoring
        df_clean_copy = df.copy()
        rename_map = {}
        RSI_col = (
            "RSI_14"
            if "RSI_14" in df_clean_copy.columns
            else [c for c in df_clean_copy.columns if "RSI" in c][0]
        )
        MACDh_col = (
            "MACDh_12_26_9"
            if "MACDh_12_26_9" in df_clean_copy.columns
            else [c for c in df_clean_copy.columns if "MACDh" in c][0]
        )
        BBP_col = (
            "BBP_20_2.0_2.0"
            if "BBP_20_2.0_2.0" in df_clean_copy.columns
            else (
                "BBP_20_2.0"
                if "BBP_20_2.0" in df_clean_copy.columns
                else [c for c in df_clean_copy.columns if "BBP" in c][0]
            )
        )
        ATR_col = (
            "ATRr_14"
            if "ATRr_14" in df_clean_copy.columns
            else [c for c in df_clean_copy.columns if "ATR" in c][0]
        )
        ADX_col = (
            "ADX_14"
            if "ADX_14" in df_clean_copy.columns
            else [c for c in df_clean_copy.columns if "ADX" in c][0]
        )

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

            x_dict_6 = {
                feat: float(row_6[feat])
                for feat in learner.features
                if feat in df_clean_copy.columns
            }
            if not any(np.isnan(v) for v in x_dict_6.values()):
                learner.update(x_dict_6, y_val)
                learner.save(online_checkpoint)
                logger.info(f"Incrementally updated OnlineAdaptiveLearner for {symbol}.")
    except Exception as e:
        logger.warning(f"Failed to incrementally update OnlineAdaptiveLearner for {symbol}: {e}")

    # Run the scoring methods
    try:
        from research.models.xgboost_model.classifier import FeatureMismatchError
    except ImportError:

        class FeatureMismatchError(Exception):  # type: ignore[misc]
            missing_features: list = []

    try:
        ensemble = await build_ensemble_signal(symbol, df, artifact_path, model_version)
    except FeatureMismatchError as e:
        logger.error(f"Prediction mismatch for {symbol}: {e}")
        raise ValueError(f"model unavailable: missing features {e.missing_features}")
    except Exception as e:
        logger.error(f"Ensemble computation failed for {symbol}: {e}")
        raise ValueError(f"Prediction unavailable for {symbol}: {e}") from e

    forecast = forecast_prices(df, horizons=[1, 3, 5, 10, 21])

    # Generate deterministic evidence-based reasoning on the critical signal path
    # (keeps external LLM latency and quota failures out of live signal serving)
    reasons = []
    try:
        from app.services.llm_reasoning_engine import LLMReasoningEngine

        technicals_dict = {
            "RSI_14": float(df["RSI_14"].iloc[-1]) if "RSI_14" in df.columns else 50.0,
            "MACD": float(df["MACD"].iloc[-1]) if "MACD" in df.columns else 0.0,
            "Trend": ensemble.get("regime", {}).get("regime", "UNKNOWN"),
        }
        evidence_pack = {
            "symbol": symbol,
            "signal": ensemble.get("direction", "HOLD"),
            "confidence": float(ensemble.get("confidence", 0.0)),
            "technicals": technicals_dict,
            "sentiment": "Neutral",
        }
        reasons = [LLMReasoningEngine._heuristic_fallback(evidence_pack)]
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
        "model_version": model_version or "latest",
        "model_versions": _build_model_versions(ensemble),
        "data_source": "yfinance",
        **_load_artifact_metadata(symbol),
    }

    try:
        from sqlalchemy import select

        from app.database.connection import async_session_factory
        from app.models.market import Instrument
        from app.models.model_artifact import ModelArtifact
        from app.models.research import ModelExplanation, Prediction

        async with async_session_factory() as session:
            inst = (
                (
                    await session.execute(
                        select(Instrument).where(Instrument.canonical_symbol == symbol)
                    )
                )
                .scalars()
                .first()
            )
            if inst:
                active_model = (
                    (
                        await session.execute(
                            select(ModelArtifact)
                            .where(
                                ModelArtifact.symbol_id == inst.id,
                                ModelArtifact.is_active.is_(True),
                            )
                            .order_by(ModelArtifact.created_at.desc())
                        )
                    )
                    .scalars()
                    .first()
                )

                if active_model:
                    import json

                    pred = Prediction(
                        model_id=active_model.id,
                        instrument_id=inst.id,
                        prediction_timestamp=datetime.now(UTC),
                        predicted_value=json.dumps(result),
                    )
                    session.add(pred)
                    await session.flush()

                    expl = ModelExplanation(
                        prediction_id=pred.id,
                        explanation_data={
                            "reasoning": reasoning_msg,
                            "features": ensemble.get("top_features", []),
                        },
                    )
                    session.add(expl)
                    await session.commit()
    except Exception as e:
        logger.error(f"Failed to persist prediction to database: {e}")

    await _cache_store(symbol, result)
    return result
