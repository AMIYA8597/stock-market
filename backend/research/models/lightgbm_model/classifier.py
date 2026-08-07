import logging

import joblib
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.calibration import CalibratedClassifierCV

logger = logging.getLogger(__name__)

class LightGBMDirectionalClassifier:
    """LightGBM wrapper for directional classification."""

    def __init__(
        self,
        max_depth: int = 5,
        learning_rate: float = 0.05,
        n_estimators: int = 100,
        calibration: str | None = "isotonic"
    ) -> None:
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.n_estimators = n_estimators
        self.calibration = calibration

        self.base_model = LGBMClassifier(
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            n_estimators=self.n_estimators,
            random_state=42,
            verbose=-1,
            # scale_pos_weight will be set during fit
        )
        self.model = None
        self.features: list[str] = []

    def fit(self, X: pd.DataFrame, y: pd.Series) -> 'LightGBMDirectionalClassifier':
        self.features = list(X.columns)

        # Handle class imbalance
        pos_weight = 1.0
        if y.sum() > 0:
            pos_weight = (len(y) - y.sum()) / y.sum()
        self.base_model.set_params(scale_pos_weight=pos_weight)

        if self.calibration:
            self.model = CalibratedClassifierCV(self.base_model, method=self.calibration, cv=5)
            self.model.fit(X, y)
            # Also fit base_model to get feature importances
            self.base_model.fit(X, y)
        else:
            self.model = self.base_model
            self.model.fit(X, y)
        return self

    def predict_proba(self, X: pd.DataFrame | dict) -> float | pd.Series:
        if isinstance(X, dict):
            X_df = pd.DataFrame([X])
        else:
            X_df = X

        X_df = X_df[self.features]
        probs = self.model.predict_proba(X_df)[:, 1]

        if isinstance(X, dict):
            return float(probs[0])
        return pd.Series(probs, index=X_df.index)

    def predict_proba_batch(self, X: pd.DataFrame) -> pd.Series:
        X_df = X[self.features]
        probs = self.model.predict_proba(X_df)[:, 1]
        return pd.Series(probs, index=X_df.index)

    def predict(self, X: pd.DataFrame) -> pd.Series:
        probs = self.predict_proba_batch(X)
        return (probs > 0.5).astype(int)

    def get_feature_importances(self) -> list[dict[str, float]]:
        if self.base_model is None:
            return []
        importances = dict(zip(self.features, self.base_model.feature_importances_, strict=False))
        sorted_imp = sorted(importances.items(), key=lambda kv: kv[1], reverse=True)[:8]
        return [{"name": k, "importance": float(v)} for k, v in sorted_imp]

    def save(self, filepath: str) -> None:
        state = {
            "model": self.model,
            "features": self.features,
            "max_depth": self.max_depth,
            "learning_rate": self.learning_rate,
            "n_estimators": self.n_estimators,
            "calibration": self.calibration
        }
        joblib.dump(state, filepath)

    @classmethod
    def load(cls, filepath: str) -> 'LightGBMDirectionalClassifier':
        state = joblib.load(filepath)
        instance = cls(
            max_depth=state["max_depth"],
            learning_rate=state["learning_rate"],
            n_estimators=state["n_estimators"],
            calibration=state["calibration"]
        )
        instance.model = state["model"]
        instance.features = state["features"]
        return instance
