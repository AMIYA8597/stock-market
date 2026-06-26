"""Ensemble Meta-Learner — Trains Logistic Regression and LightGBM on layer scores."""

from __future__ import annotations

import os
import pickle
import logging
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Tuple
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV, FrozenEstimator
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import brier_score_loss, accuracy_score
import lightgbm as lgb

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent.parent.parent.parent / "data" / "models"

class EnsembleMetaLearner:
    """Trains meta-models on sub-scores to predict direction probability."""

    def __init__(self, model_type: str = "logistic"):
        self.model_type = model_type
        self.lr_model: CalibratedClassifierCV | None = None
        self.lgb_model: CalibratedClassifierCV | None = None
        self.feature_names = ["technical", "pattern", "momentum", "regime", "xgboost", "sentiment"]
        self.best_model_name = "logistic"

    def save(self, path: Path | str | None = None) -> None:
        """Serialize meta-learner instance to disk."""
        os.makedirs(MODEL_DIR, exist_ok=True)
        target_path = path or (MODEL_DIR / "ensemble_meta_learner.pkl")
        with open(target_path, "wb") as f:
            pickle.dump(self, f)
        logger.info(f"EnsembleMetaLearner saved to {target_path}")

    @classmethod
    def load(cls, path: Path | str | None = None) -> EnsembleMetaLearner:
        """Load meta-learner instance from disk."""
        target_path = path or (MODEL_DIR / "ensemble_meta_learner.pkl")
        if not os.path.exists(target_path):
            logger.warning(f"Meta-learner checkpoint not found at {target_path}, returning default instance.")
            return cls()
        with open(target_path, "rb") as f:
            obj = pickle.load(f)
        logger.info(f"EnsembleMetaLearner loaded from {target_path}")
        return obj

    def prepare_training_data(self, symbols: List[str]) -> Tuple[pd.DataFrame, pd.Series]:
        """Fetch historical data and generate sub-scores for training."""
        from app.services.prediction_engine import get_full_prediction
        import yfinance as yf

        X_list = []
        y_list = []

        # Make imports dynamic to avoid circular dependencies
        from app.services.prediction_engine import (
            score_technical,
            score_patterns,
            score_momentum,
            detect_regime,
            score_xgboost,
        )

        for symbol in symbols:
            logger.info(f"Generating training data for {symbol}...")
            # Fetch 2 years of history
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="2y", interval="1d")
            if df.empty or len(df) < 120:
                logger.warning(f"Insufficient history for {symbol}")
                continue

            df.columns = [c.lower() for c in df.columns]
            df = df.rename(columns={"stock splits": "stock_splits", "capital gains": "capital_gains"})
            df = df[["open", "high", "low", "close", "volume"]].dropna()
            df = df.reset_index().rename(columns={"Date": "time", "Datetime": "time"})
            df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)
            df.index = pd.DatetimeIndex(df["time"])
            df.index.name = None

            # Add required indicator features to df
            from research.feature_engineering.price_factors import PriceFactorsBuilder
            from research.feature_engineering.volatility_factors import VolatilityFactorsBuilder
            df = PriceFactorsBuilder().transform(df)
            df = VolatilityFactorsBuilder().transform(df)

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
            cols_to_drop = [c for c in df.columns if "SUPERTl" in c or "SUPERTs" in c]
            df = df.drop(columns=cols_to_drop, errors="ignore")
            
            # Standardize column names
            rename_map = {}
            RSI_col = "RSI_14" if "RSI_14" in df.columns else [c for c in df.columns if "RSI" in c][0]
            MACDh_col = "MACDh_12_26_9" if "MACDh_12_26_9" in df.columns else [c for c in df.columns if "MACDh" in c][0]
            BBP_col = "BBP_20_2.0_2.0" if "BBP_20_2.0_2.0" in df.columns else ("BBP_20_2.0" if "BBP_20_2.0" in df.columns else [c for c in df.columns if "BBP" in c][0])
            ATR_col = "ATRr_14" if "ATRr_14" in df.columns else [c for c in df.columns if "ATR" in c][0]
            ADX_col = "ADX_14" if "ADX_14" in df.columns else [c for c in df.columns if "ADX" in c][0]
            
            if RSI_col != "RSI_14": rename_map[RSI_col] = "RSI_14"
            if MACDh_col != "MACDh_12_26_9": rename_map[MACDh_col] = "MACDh_12_26_9"
            if BBP_col != "BBP_20_2.0": rename_map[BBP_col] = "BBP_20_2.0"
            if ATR_col != "ATRr_14": rename_map[ATR_col] = "ATRr_14"
            if ADX_col != "ADX_14": rename_map[ADX_col] = "ADX_14"
            
            if rename_map:
                df = df.rename(columns=rename_map)

            df = df.replace([np.inf, -np.inf], np.nan).dropna()

            if len(df) < 100:
                continue

            # Target: 5-day forward return direction
            df["target_5d"] = (df["close"].shift(-5) / df["close"]) - 1.0
            df["label"] = (df["target_5d"] > 0).astype(int)

            # We generate walk-forward predictions for XGBoost with a step size of 21 days
            xgb_scores = np.zeros(len(df))
            
            # Simple walk forward XGBoost simulation to prevent lookahead bias
            # Start at index 60
            for idx in range(60, len(df)):
                # We train a quick XGBoost model using data up to idx-6 to predict at idx
                df_slice = df.iloc[:idx+1]
                # To make it fast, we fit a model every 21 steps and predict the block,
                # but for simplicity and correctness, let's train a lightweight XGBoost model
                # on historical slice.
                if idx % 21 == 0 or idx == 60:
                    train_df = df.iloc[:idx-5]
                    # Simple train
                    import xgboost as xgb
                    from sklearn.preprocessing import StandardScaler
                    features_xgb = [
                        "ret_1d", "ret_5d", "ret_21d", "momentum_63d",
                        "RSI_14", "MACDh_12_26_9", "BBP_20_2.0", "ATRr_14",
                        "ADX_14", "realized_vol_21d", "yang_zhang_vol_21d",
                        "dist_52w_high", "dist_52w_low", "drawdown",
                        "range_pct", "close_to_open"
                    ]
                    # Rename columns to avoid key errors
                    X_train = train_df[features_xgb].dropna()
                    y_train = train_df["label"].loc[X_train.index]
                    if len(X_train) > 20:
                        scaler = StandardScaler()
                        X_train_s = scaler.fit_transform(X_train)
                        clf = xgb.XGBClassifier(
                            n_estimators=30, max_depth=3, learning_rate=0.1,
                            use_label_encoder=False, eval_metric="logloss",
                            random_state=42, verbosity=0
                        )
                        clf.fit(X_train_s, y_train)
                        self_scaler = scaler
                        self_clf = clf
                    else:
                        self_clf = None
                
                if 'self_clf' in locals() and self_clf is not None:
                    row = df.iloc[[idx]][features_xgb]
                    if not row.isnull().any().any():
                        row_s = self_scaler.transform(row)
                        prob = float(self_clf.predict_proba(row_s)[0][1])
                        xgb_scores[idx] = (prob - 0.5) * 2.0
                    else:
                        xgb_scores[idx] = 0.0
                else:
                    xgb_scores[idx] = 0.0

            # Compute other subscores for each row from index 60 onwards
            for idx in range(60, len(df) - 5):
                df_slice = df.iloc[:idx+1]
                tech = score_technical(df_slice)
                patt = score_patterns(df_slice)
                mom = score_momentum(df_slice)
                
                # Fast regime detection proxy to prevent statsmodels loop overhead
                ret_63d = float((df_slice["close"].iloc[-1] / df_slice["close"].iloc[max(0, len(df_slice)-64)]) - 1.0) if len(df_slice) >= 64 else 0.0
                realized_vol = float(np.log(df_slice["close"]/df_slice["close"].shift(1)).rolling(21).std().iloc[-1]) if len(df_slice) >= 22 else 0.02
                ann_vol = realized_vol * np.sqrt(252)
                sharpe_proxy = ret_63d / (ann_vol + 1e-6)
                reg_val = 1.0 if sharpe_proxy > 0.5 else (-1.0 if sharpe_proxy < -0.5 else 0.0)
                
                # Lookahead-free simulated sentiment score based on past 5-day return and deterministic noise
                ret_5d = float(df_slice["ret_5d"].iloc[-1]) if "ret_5d" in df_slice.columns else 0.0
                dt_str = str(df["time"].iloc[idx])
                noise_val = (((sum(ord(c) for c in dt_str) + sum(ord(c) for c in symbol)) % 100) / 500.0) - 0.1
                sentiment_score = float(np.clip(1.5 * ret_5d + noise_val, -1.0, 1.0))

                X_list.append({
                    "technical": tech["score"],
                    "pattern": patt["pattern_score"],
                    "momentum": mom["momentum_score"],
                    "regime": reg_val,
                    "xgboost": xgb_scores[idx],
                    "sentiment": sentiment_score,
                    "target_5d": float(df["target_5d"].iloc[idx]),
                    "close": float(df["close"].iloc[idx]),
                })
                y_list.append(df["label"].iloc[idx])

        return pd.DataFrame(X_list), pd.Series(y_list)

    def train(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """Train models using TimeSeriesSplit and CalibratedClassifierCV."""
        tscv = TimeSeriesSplit(n_splits=5)
        
        lr_briers = []
        lgb_briers = []
        old_briers = []

        # Iterate splits for validation
        for train_idx, test_idx in tscv.split(X):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

            X_train_feat = X_train[self.feature_names]
            X_test_feat = X_test[self.feature_names]

            # 1. Old fixed weight prediction probability proxy
            # fixed weights: tech:0.3, patt:0.15, mom:0.2, reg:0.1, xgb:0.25
            old_signal = (
                X_test_feat["technical"] * 0.30 +
                X_test_feat["pattern"] * 0.15 +
                X_test_feat["momentum"] * 0.20 +
                X_test_feat["regime"] * 0.10 +
                X_test_feat["xgboost"] * 0.25
            )
            old_prob = (old_signal + 1.0) / 2.0
            old_brier = brier_score_loss(y_test, old_prob)
            old_briers.append(old_brier)

            # 2. Logistic Regression
            lr = LogisticRegression(random_state=42)
            lr.fit(X_train_feat, y_train)
            cal_lr = CalibratedClassifierCV(estimator=FrozenEstimator(lr), method="sigmoid")
            cal_lr.fit(X_train_feat, y_train) # Platt scaling
            lr_prob = cal_lr.predict_proba(X_test_feat)[:, 1]
            lr_briers.append(brier_score_loss(y_test, lr_prob))

            # 3. LightGBM
            lgb_clf = lgb.LGBMClassifier(n_estimators=30, max_depth=3, learning_rate=0.05, random_state=42, verbose=-1)
            lgb_clf.fit(X_train_feat, y_train)
            cal_lgb = CalibratedClassifierCV(estimator=FrozenEstimator(lgb_clf), method="isotonic")
            cal_lgb.fit(X_train_feat, y_train)
            lgb_prob = cal_lgb.predict_proba(X_test_feat)[:, 1]
            lgb_briers.append(brier_score_loss(y_test, lgb_prob))

        # Train final models on entire dataset
        lr_final = LogisticRegression(random_state=42)
        self.lr_model = CalibratedClassifierCV(estimator=lr_final, method="sigmoid", cv=5)
        self.lr_model.fit(X[self.feature_names], y)

        lgb_final = lgb.LGBMClassifier(n_estimators=30, max_depth=3, learning_rate=0.05, random_state=42, verbose=-1)
        self.lgb_model = CalibratedClassifierCV(estimator=lgb_final, method="isotonic", cv=5)
        self.lgb_model.fit(X[self.feature_names], y)

        # Log coefficients and feature importances
        coefs = self.lr_model.calibrated_classifiers_[0].estimator.coef_[0]
        logger.info("Logistic Regression Meta-learner coefficients:")
        for name, coef in zip(self.feature_names, coefs):
            logger.info(f"  {name}: {coef:.4f}")

        mean_lr_brier = np.mean(lr_briers)
        mean_lgb_brier = np.mean(lgb_briers)
        mean_old_brier = np.mean(old_briers)

        logger.info(f"Mean Out-Of-Sample Brier Scores:")
        logger.info(f"  Old Fixed-Weight: {mean_old_brier:.5f}")
        logger.info(f"  Logistic Meta:    {mean_lr_brier:.5f}")
        logger.info(f"  LightGBM Meta:    {mean_lgb_brier:.5f}")

        # Determine winner based on Brier score (lower is better)
        if mean_lr_brier <= mean_lgb_brier:
            self.best_model_name = "logistic"
        else:
            self.best_model_name = "lightgbm"

        logger.info(f"Selected best ensemble meta-learner model: {self.best_model_name}")

        return {
            "old_fixed_brier": mean_old_brier,
            "logistic_brier": mean_lr_brier,
            "lightgbm_brier": mean_lgb_brier,
            "best_model": self.best_model_name,
            "coefficients": dict(zip(self.feature_names, [float(c) for c in coefs]))
        }

    def predict_proba(self, scores: List[float]) -> float:
        """Predict the probability of upward movement from layer scores."""
        X_pred = pd.DataFrame([scores], columns=self.feature_names)
        if self.best_model_name == "logistic" and self.lr_model is not None:
            return float(self.lr_model.predict_proba(X_pred)[0][1])
        elif self.lgb_model is not None:
            return float(self.lgb_model.predict_proba(X_pred)[0][1])
        else:
            # Fallback to simple average or predefined weights if not trained
            WEIGHTS = [0.30, 0.15, 0.20, 0.10, 0.25]
            raw = sum(s * w for s, w in zip(scores, WEIGHTS))
            return float(np.clip((raw + 1.0) / 2.0, 0.0, 1.0))
