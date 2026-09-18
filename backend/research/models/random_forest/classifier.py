from __future__ import annotations

import logging
import pickle
from pathlib import Path

import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier

logger = logging.getLogger(__name__)

class FeatureMismatchError(ValueError):
    def __init__(self, missing_features: list[str]):
        self.missing_features = missing_features
        super().__init__(f"model unavailable: missing features {missing_features}")

class ClassicalDirectionalClassifier:
    def __init__(self, model_type='random_forest', n_estimators=100, max_depth=6, random_state=42):
        self.features = []
        self.model_type = model_type
        if model_type == 'random_forest':
            self.model = RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=random_state)
        elif model_type == 'extra_trees':
            self.model = ExtraTreesClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=random_state)
        else:
            raise ValueError("Unsupported model_type")

    def fit(self, X: pd.DataFrame, y: pd.Series):
        self.features = list(X.columns)
        self.model.fit(X, y)
        return self

    def predict_proba(self, X: pd.DataFrame) -> float:
        missing = [f for f in self.features if f not in X.columns]
        if missing:
            raise FeatureMismatchError(missing)
        return self.model.predict_proba(X[self.features])[0][1]

    def predict_proba_batch(self, X: pd.DataFrame) -> pd.Series:
        missing = [f for f in self.features if f not in X.columns]
        if missing:
            raise FeatureMismatchError(missing)
        probs = self.model.predict_proba(X[self.features])[:, 1]
        return pd.Series(probs, index=X.index)

    def save(self, path: Path | str) -> None:
        with open(path, 'wb') as f:
            pickle.dump(self, f)

    @classmethod
    def load(cls, path: Path | str):
        if not Path(path).exists():
            return None
        with open(path, 'rb') as f:
            return pickle.load(f)
