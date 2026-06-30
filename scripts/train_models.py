#!/usr/bin/env python3
"""
NEUROQUANT Model Training Orchestrator
Trains all active models (XGBoost, LSTM-Attention, Quantile LGB) and saves them to disk.
"""

import sys
import logging
from pathlib import Path

# Ensure project root is on PYTHONPATH
project_root = Path(__file__).resolve().parent.parent / "backend"
sys.path.append(str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting NEUROQUANT model training...")
    
    from tasks.training_tasks import retrain_model
    
    # Retrain XGBoost
    logger.info("Retraining XGBoost models...")
    res_xgb = retrain_model("xgboost")
    logger.info(f"XGBoost retraining completed: {res_xgb}")
    
    # Retrain LSTM Attention
    logger.info("Retraining LSTM-Attention models...")
    res_lstm = retrain_model("lstm_attention")
    logger.info(f"LSTM-Attention retraining completed: {res_lstm}")
    
    # Retrain Quantile Forecaster
    logger.info("Retraining Quantile Forecaster models...")
    res_qf = retrain_model("quantile_forecaster")
    logger.info(f"Quantile Forecaster retraining completed: {res_qf}")
    
    # Retrain Online Adaptive Learner
    logger.info("Retraining Online Adaptive Learner models...")
    res_ol = retrain_model("online_learner")
    logger.info(f"Online Learner retraining completed: {res_ol}")

    logger.info("All model training complete!")

if __name__ == "__main__":
    main()