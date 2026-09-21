import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from research.models.xgboost_model.classifier import XGBoostDirectionalClassifier


def test_shap():
    print("Running SHAP consistency test...")
    artifact_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/artifacts/xgboost_A_6d8d915f.pkl"))
    clf = XGBoostDirectionalClassifier.load(artifact_path)

    if not clf:
        print("Model artifact not found. Please ensure it exists.")
        return

    # Create dummy dataframe matching features
    dummy_data = {feat: [np.random.randn()] for feat in clf.features}
    df = pd.DataFrame(dummy_data)

    # 1. Get raw SHAP values via the explainer directly
    from research.explainability.shap_explainer import get_tree_shap
    X_scaled = clf.scaler.transform(df[clf.features])
    booster = clf.base_model.get_booster()
    expl = get_tree_shap(booster, X_scaled, feature_names=clf.features)

    shap_sum = float(np.sum(expl.values[0]))
    base_value = float(expl.base_value)

    # SHAP margin = sum(shap_values) + base_value
    shap_margin = shap_sum + base_value

    # 2. Get the model's logit (margin output) directly from XGBoost
    import xgboost as xgb
    dmatrix = xgb.DMatrix(X_scaled)
    # output_margin=True returns the logit before sigmoid/calibration
    logit_output = float(booster.predict(dmatrix, output_margin=True)[0])

    print(f"SHAP sum:      {shap_sum:.6f}")
    print(f"Base value:    {base_value:.6f}")
    print(f"SHAP margin:   {shap_margin:.6f}")
    print(f"Model logit:   {logit_output:.6f}")

    # 3. Assert consistency
    diff = abs(shap_margin - logit_output)
    print(f"Difference:    {diff:.6f}")

    assert diff < 1e-4, f"SHAP consistency failed! Difference {diff} is too large."
    print("SUCCESS: SHAP values perfectly match the model's raw logit output.")

if __name__ == "__main__":
    test_shap()
