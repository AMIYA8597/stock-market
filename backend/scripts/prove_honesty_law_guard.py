import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tasks.training_tasks import train_single_xgboost
from unittest.mock import patch
import numpy as np

def mock_xgboost_fit(self, X, y):
    pass

def mock_xgboost_predict_proba(self, X):
    # Always predict exactly what the label will be (100% accuracy leak)
    # The true target is derived in training_tasks via df["label"]
    # We'll just monkeypatch the predict_proba to return 1.0 if it's supposed to be positive
    # But since predict_proba gets just the features, it's hard to know the label.
    # Instead, let's mock generate_cpcv_splits or np.mean to force win_rate > 0.75
    return 1.0

def main():
    print("Testing Honesty Law Guard in Training Pipeline...")
    
    # We can mock np.mean so that when it calculates win_rate = np.mean(predictions == actuals), it returns 0.99
    original_mean = np.mean
    
    def side_effect_mean(a, *args, **kwargs):
        if hasattr(a, 'shape') and a.dtype == bool:
            return 0.99 # Mock 99% accuracy
        return original_mean(a, *args, **kwargs)

    with patch('numpy.mean', side_effect=side_effect_mean):
        try:
            train_single_xgboost("RELIANCE.NS")
            print("FAILED: Model trained and saved successfully despite >75% accuracy.")
        except ValueError as e:
            if "LeakageError" in str(e):
                print(f"SUCCESS: Honesty Law guard blocked leaky model promotion.\nError: {e}")
            else:
                print(f"FAILED with unexpected ValueError: {e}")
        except Exception as e:
            print(f"FAILED with unexpected exception: {e}")

if __name__ == "__main__":
    main()
