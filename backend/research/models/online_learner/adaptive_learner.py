"""Online Adaptive Learner — Incremental model updates using River."""

from __future__ import annotations

import os
import pickle
import logging
from pathlib import Path
import river
from river import compose
from river import preprocessing
from river import linear_model

logger = logging.getLogger(__name__)

class OnlineAdaptiveLearner:
    """Incremental learner using a River pipeline of StandardScaler and Logistic Regression."""

    def __init__(self) -> None:
        self.model = compose.Pipeline(
            preprocessing.StandardScaler(),
            linear_model.LogisticRegression(optimizer=river.optim.SGD(0.01))
        )
        self.features = [
            "ret_1d", "ret_5d", "ret_21d", "momentum_63d",
            "RSI_14", "MACDh_12_26_9", "BBP_20_2.0", "ATRr_14",
            "ADX_14", "realized_vol_21d", "yang_zhang_vol_21d",
            "dist_52w_high", "dist_52w_low", "drawdown",
            "range_pct", "close_to_open"
        ]

    def update(self, x_dict: dict[str, float], y: int) -> None:
        """Update the model with a single observation incrementally."""
        x_clean = {f: float(x_dict.get(f, 0.0)) for f in self.features}
        # River classification target is expected to be boolean
        self.model.learn_one(x_clean, bool(y))

    def predict_proba(self, x_dict: dict[str, float]) -> float:
        """Predict the probability of upward movement (Class 1)."""
        x_clean = {f: float(x_dict.get(f, 0.0)) for f in self.features}
        res = self.model.predict_proba_one(x_clean)
        # res behaves like a dictionary/Counter of {True: p_true, False: p_false}
        return float(res.get(True, 0.5))

    def save(self, path: Path | str) -> None:
        """Save the online learner to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: Path | str) -> OnlineAdaptiveLearner:
        """Load the online learner from disk, or return a new instance if missing."""
        if not os.path.exists(path):
            return cls()
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Failed to load OnlineAdaptiveLearner from {path}: {e}")
            return cls()
