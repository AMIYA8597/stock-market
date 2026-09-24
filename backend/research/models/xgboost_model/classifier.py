"""XGBoost Walk-Forward Directional Classifier."""

from __future__ import annotations

import logging
import os
import pickle
from pathlib import Path
from typing import Any

import pandas as pd
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class FeatureMismatchError(ValueError):
    """Raised when features needed for the model prediction are missing in input."""

    def __init__(self, missing_features: list[str]):
        self.missing_features = missing_features
        super().__init__(f"model unavailable: missing features {missing_features}")


class XGBoostDirectionalClassifier:
    """XGBoost classifier for predicting directional price movement."""

    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 4,
        learning_rate: float = 0.05,
        calibration: str = "isotonic",
    ):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.calibration = calibration
        self.model = None
        self.base_model = None
        self.scaler = StandardScaler()
        self.features = [
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
            # Phase A1 features
            "sentiment_score",
            "news_volume",
            "sentiment_pos_neg_ratio",
            "market_sentiment_index",
            "sentiment_momentum_3d",
            # Phase A2 features
            "regime_state",
            "garch_vol",
        ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> XGBoostDirectionalClassifier:
        """Fit the scaler and classifier."""
        missing = [f for f in self.features if f not in X.columns]
        if missing:
            # For testing with incomplete datasets, just drop missing features
            self.features = [f for f in self.features if f in X.columns]

        X_clean = X[self.features].dropna()
        y_clean = y.loc[X_clean.index]

        X_scaled = self.scaler.fit_transform(X_clean)

        # Scale pos weight to handle class imbalance
        pos_weight = 1.0
        if y_clean.sum() > 0:
            pos_weight = (len(y_clean) - y_clean.sum()) / y_clean.sum()

        self.base_model = xgb.XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=pos_weight,
            eval_metric="logloss",
            random_state=42,
            verbosity=0,
        )

        # Calibrate probabilities
        if self.calibration:
            from sklearn.model_selection import TimeSeriesSplit
            tscv = TimeSeriesSplit(n_splits=3)
            self.model = CalibratedClassifierCV(
                estimator=self.base_model, method=self.calibration, cv=tscv
            )
        else:
            self.model = self.base_model

        self.model.fit(X_scaled, y_clean)

        # Extract feature importances
        if self.calibration:
            self.base_model.fit(X_scaled, y_clean)

        return self

    def predict_proba(self, X: pd.DataFrame) -> float:
        """Predict probability of upward movement (class 1)."""
        missing_features = [f for f in self.features if f not in X.columns]
        if missing_features:
            raise FeatureMismatchError(missing_features)

        if self.model is None:
            return 0.5

        X_clean = X[self.features]
        X_scaled = self.scaler.transform(X_clean)
        return float(self.model.predict_proba(X_scaled)[0][1])

    def predict_proba_batch(self, X: pd.DataFrame) -> pd.Series:
        missing_features = [f for f in self.features if f not in X.columns]
        if missing_features:
            raise FeatureMismatchError(missing_features)

        if self.model is None:
            return pd.Series(0.5, index=X.index)

        X_clean = X[self.features]
        X_scaled = self.scaler.transform(X_clean)
        probs = self.model.predict_proba(X_scaled)[:, 1]
        return pd.Series(probs, index=X.index)

    def get_feature_importances(self) -> list[dict[str, Any]]:
        """Get sorted list of features and importances."""
        if self.base_model is None:
            return []
        importances = dict(zip(self.features, self.base_model.feature_importances_, strict=False))
        sorted_imp = sorted(importances.items(), key=lambda kv: kv[1], reverse=True)[:8]
        return [{"name": k, "importance": float(v)} for k, v in sorted_imp]

    def get_shap_values(self, X: pd.DataFrame) -> list[dict[str, Any]]:
        """Compute real SHAP values for a single row using shap_explainer."""
        if self.base_model is None:
            return []

        try:
            from research.explainability.shap_explainer import get_tree_shap

            X_clean = X[self.features].iloc[-1:]  # Just the last row
            X_scaled = self.scaler.transform(X_clean)

            # base_model is an XGBClassifier, we can get booster
            booster = self.base_model.get_booster()
            expl = get_tree_shap(booster, X_scaled, feature_names=self.features)

            # The explanation values are for a single row
            shap_row = expl.values[0]

            res = []
            for i, feat_name in enumerate(self.features):
                res.append({"name": feat_name, "shap_value": float(shap_row[i])})

            sorted_res = sorted(res, key=lambda x: abs(x["shap_value"]), reverse=True)[:10]
            return sorted_res, float(expl.base_value)
        except Exception as e:
            logger.error(f"SHAP extraction failed: {e}")
            # Fallback
            return self.get_feature_importances(), 0.5

    def save(self, path: Path | str) -> None:
        """Save model and scaler to a file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        state = {
            "scaler": self.scaler,
            "features": self.features,
            "model": self.model,
            "base_model": self.base_model,
        }
        with open(path, "wb") as f:
            pickle.dump(state, f)

    @classmethod
    def load(cls, path: Path | str) -> XGBoostDirectionalClassifier | None:
        """Load model and scaler from a file."""
        if not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as f:
                state = pickle.load(f)

            inst = cls()
            if isinstance(state, dict) and "model" in state:
                inst.scaler = state.get("scaler")
                inst.features = state.get("features", inst.features)
                inst.model = state.get("model")
                inst.base_model = state.get("base_model")
            else:
                # If state is a raw XGBoostDirectionalClassifier instance
                inst = state
            return inst
        except Exception as e:
            logger.error(f"Failed to load XGBoost model from {path}: {e}")
            return None
