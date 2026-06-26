"""XGBoost Walk-Forward Directional Classifier."""

from __future__ import annotations

import os
import pickle
import logging
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

class XGBoostDirectionalClassifier:
    """XGBoost classifier for predicting directional price movement."""

    def __init__(self, n_estimators: int = 100, max_depth: int = 4, learning_rate: float = 0.05):
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.model = None
        self.scaler = StandardScaler()
        self.features = [
            "ret_1d", "ret_5d", "ret_21d", "momentum_63d",
            "RSI_14", "MACDh_12_26_9", "BBP_20_2.0", "ATRr_14",
            "ADX_14", "realized_vol_21d", "yang_zhang_vol_21d",
            "dist_52w_high", "dist_52w_low", "drawdown",
            "range_pct", "close_to_open"
        ]

    def fit(self, X: pd.DataFrame, y: pd.Series) -> XGBoostDirectionalClassifier:
        """Fit the scaler and classifier."""
        X_clean = X[self.features].dropna()
        y_clean = y.loc[X_clean.index]
        
        X_scaled = self.scaler.fit_transform(X_clean)
        
        self.model = xgb.XGBClassifier(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=0.8,
            colsample_bytree=0.8,
            use_label_encoder=False,
            eval_metric="logloss",
            random_state=42,
            verbosity=0
        )
        self.model.fit(X_scaled, y_clean)
        return self

    def predict_proba(self, X: pd.DataFrame) -> float:
        """Predict probability of upward movement (class 1)."""
        if self.model is None:
            return 0.5
        X_clean = X[self.features]
        X_scaled = self.scaler.transform(X_clean)
        return float(self.model.predict_proba(X_scaled)[0][1])

    def get_feature_importances(self) -> list[dict[str, Any]]:
        """Get sorted list of features and importances."""
        if self.model is None:
            return []
        importances = dict(zip(self.features, self.model.feature_importances_))
        sorted_imp = sorted(importances.items(), key=lambda kv: kv[1], reverse=True)[:8]
        return [{"name": k, "importance": float(v)} for k, v in sorted_imp]

    def save(self, path: Path | str) -> None:
        """Save model and scaler to a file."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: Path | str) -> XGBoostDirectionalClassifier | None:
        """Load model and scaler from a file."""
        if not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Failed to load XGBoost model from {path}: {e}")
            return None
