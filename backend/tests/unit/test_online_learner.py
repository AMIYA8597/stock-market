from __future__ import annotations

import os
import tempfile
from pathlib import Path
import numpy as np
import pytest

from research.models.online_learner import OnlineAdaptiveLearner

def test_online_learner_flow():
    # 1. Initialize learner
    learner = OnlineAdaptiveLearner()
    assert len(learner.features) == 16
    
    # 2. Make mock data row
    mock_row = {feat: 0.1 for feat in learner.features}
    
    # 3. Predict before any updates (should return default probability 0.5)
    prob_init = learner.predict_proba(mock_row)
    assert 0.0 <= prob_init <= 1.0
    
    # 4. Perform multiple incremental updates
    # Let's train on 20 samples of positive class and 20 of negative class
    for i in range(20):
        # positive features
        pos_row = {feat: 1.0 + np.random.normal(0, 0.1) for feat in learner.features}
        learner.update(pos_row, 1)
        
        # negative features
        neg_row = {feat: -1.0 + np.random.normal(0, 0.1) for feat in learner.features}
        learner.update(neg_row, 0)
        
    # 5. Predict on positive and negative cases
    pos_test = {feat: 1.2 for feat in learner.features}
    neg_test = {feat: -1.2 for feat in learner.features}
    
    prob_pos = learner.predict_proba(pos_test)
    prob_neg = learner.predict_proba(neg_test)
    
    # Positive case should have higher probability of Class 1 than negative case
    assert prob_pos > prob_neg
    
    # 6. Test save and load serialization
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "online_model.pkl"
        learner.save(model_path)
        assert model_path.exists()
        
        loaded_learner = OnlineAdaptiveLearner.load(model_path)
        assert len(loaded_learner.features) == 16
        
        # Predictions of loaded model should match the original model
        assert loaded_learner.predict_proba(pos_test) == prob_pos
        assert loaded_learner.predict_proba(neg_test) == prob_neg
