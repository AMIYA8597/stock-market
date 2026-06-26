from __future__ import annotations

import numpy as np
import pandas as pd
from research.models.ensemble.meta_learner import EnsembleMetaLearner

def test_meta_learner_train_predict() -> None:
    # Build synthetic features representing the layer scores and label
    np.random.seed(42)
    n_samples = 200
    
    # 6 features: ["technical", "pattern", "momentum", "regime", "xgboost", "sentiment"]
    X = pd.DataFrame({
        "technical": np.random.uniform(-1, 1, n_samples),
        "pattern": np.random.uniform(-1, 1, n_samples),
        "momentum": np.random.uniform(-1, 1, n_samples),
        "regime": np.random.choice([-1.0, 0.0, 1.0], n_samples),
        "xgboost": np.random.uniform(-1, 1, n_samples),
        "sentiment": np.random.uniform(-1, 1, n_samples)
    })
    # Target label: correlated with features
    y_prob = 1 / (1 + np.exp(-(X["technical"] * 0.5 + X["xgboost"] * 0.8 + X["sentiment"] * 0.4)))
    y = pd.Series((y_prob > np.random.rand(n_samples)).astype(int))

    learner = EnsembleMetaLearner()
    metrics = learner.train(X, y)
    
    assert "logistic_brier" in metrics
    assert "lightgbm_brier" in metrics
    assert "best_model" in metrics
    
    # Predict probability for a single score vector
    test_scores = [0.2, 0.1, 0.3, 1.0, 0.4, 0.2]
    prob = learner.predict_proba(test_scores)
    assert 0.0 <= prob <= 1.0
