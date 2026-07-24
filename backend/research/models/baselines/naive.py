"""Naive Baseline for Directional Classification."""

from __future__ import annotations

import pandas as pd


class NaiveDirectionalClassifier:
    """Naive persistence baseline. Predicts tomorrow's direction equals today's direction.

    If today's return was > 0, it predicts Up (1). Otherwise, Down (0).
    """

    def __init__(self) -> None:
        pass

    def fit(self, X: pd.DataFrame, y: pd.Series) -> NaiveDirectionalClassifier:
        """No training required."""
        return self

    def predict_proba(self, X: pd.DataFrame) -> pd.Series:
        """Predicts probability 1.0 if today was up, else 0.0."""
        # Requires 'ret_1d' in X which represents today's return.
        if "ret_1d" not in X.columns:
            raise ValueError("Naive baseline requires 'ret_1d' feature.")

        # If today > 0 -> 1.0 (100% confidence it will go up)
        # If today <= 0 -> 0.0 (0% confidence it will go up -> meaning it will go down)
        probs = (X["ret_1d"] > 0).astype(float)
        return probs
