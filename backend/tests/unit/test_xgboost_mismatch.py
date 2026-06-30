from __future__ import annotations

import pandas as pd
import pytest
from research.models.xgboost_model.classifier import XGBoostDirectionalClassifier, FeatureMismatchError

def test_xgboost_feature_mismatch_raises_error() -> None:
    clf = XGBoostDirectionalClassifier()
    # Create a DataFrame missing required features
    df = pd.DataFrame(columns=["ret_1d", "ret_5d"])
    
    with pytest.raises(FeatureMismatchError) as exc_info:
        clf.predict_proba(df)
        
    assert "model unavailable: missing features" in str(exc_info.value)
    # Check that it identifies the missing columns (should be more than 10)
    assert len(exc_info.value.missing_features) > 10
