import os
import sys

# Add backend to path so imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import logging
from research.models.tft.quantile_forecaster import QuantileLGBForecaster

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def evaluate_tft(symbol="RELIANCE.NS"):
    logger.info(f"Evaluating QuantileLGBForecaster (TFT-Lite) on {symbol}")
    
    forecaster = QuantileLGBForecaster()
    
    # Prepare data
    logger.info("Fetching historical data and building features...")
    X, y = forecaster.prepare_training_data([symbol])
    
    if X.empty:
        logger.error("No data prepared.")
        return
        
    logger.info(f"Data shape: {X.shape}")
    
    # Simple walk-forward evaluation (similar to training_pipeline.py)
    train_size = 200
    test_size = 50
    
    if len(X) < train_size + test_size:
        logger.error("Not enough data for walk-forward CV.")
        return
        
    all_preds_p10 = []
    all_preds_p50 = []
    all_preds_p90 = []
    all_y = []
    
    for start_idx in range(0, len(X) - train_size - test_size + 1, test_size):
        end_train = start_idx + train_size
        end_test = end_train + test_size
        
        # Expanding window for training
        X_train = X.iloc[0:end_train]
        y_train = y.iloc[0:end_train]
        
        X_test = X.iloc[end_train:end_test]
        y_test = y.iloc[end_train:end_test]
        
        # Train on this fold
        forecaster.train(X_train, y_train)
        
        # Predict on this fold
        for i in range(len(X_test)):
            p10, p50, p90 = forecaster.predict(X_test.iloc[i].to_dict())
            all_preds_p10.append(p10)
            all_preds_p50.append(p50)
            all_preds_p90.append(p90)
            all_y.append(y_test.iloc[i])
            
    # Calculate directional accuracy of the median (P50)
    # Target is 5-day return, so direction is return > 0
    import numpy as np
    y_true_dir = (np.array(all_y) > 0).astype(int)
    y_pred_dir = (np.array(all_preds_p50) > 0).astype(int)
    
    from sklearn.metrics import accuracy_score
    acc = accuracy_score(y_true_dir, y_pred_dir)
    
    # Check coverage of 80% confidence interval [P10, P90]
    in_bounds = [(all_y[i] >= all_preds_p10[i] and all_y[i] <= all_preds_p90[i]) for i in range(len(all_y))]
    coverage = np.mean(in_bounds)
    
    logger.info("\n### TFT (QuantileLGB) Walk-Forward Evaluation Metrics\n")
    logger.info(f"Total test samples: {len(all_y)}")
    logger.info(f"P50 Directional Accuracy: {acc:.4f}")
    logger.info(f"Empirical Coverage of [P10, P90] Interval: {coverage:.4f} (Expected ~0.80)")
    
    # Log the first 5 predictions to prove it's a real trained spread, not just post-hoc scalar addition
    logger.info("\nFirst 5 Predictions (P10, P50, P90) vs Actual:")
    for i in range(5):
        logger.info(f"Target: {all_y[i]:.4f} | Preds: [{all_preds_p10[i]:.4f}, {all_preds_p50[i]:.4f}, {all_preds_p90[i]:.4f}] | Width: {all_preds_p90[i] - all_preds_p10[i]:.4f}")

if __name__ == "__main__":
    evaluate_tft()
