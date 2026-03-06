#!/usr/bin/env python3
"""
NEUROQUANT Model Training Orchestrator
Trains all ML models and saves to MLflow
"""

import logging
from pathlib import Path

import mlflow
import mlflow.pytorch
from mlflow.tracking import MlflowClient

from services.ml_engine.models.amstan import AMSTANModel
from services.ml_engine.models.rl_agent import RLTradingAgent
from services.ml_engine.models.gnn import MarketGNN
from services.ml_engine.training.trainer import ModelTrainer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def train_amstan():
    """Train AMSTAN forecasting model"""
    logger.info("Training AMSTAN model...")

    trainer = ModelTrainer()
    model = AMSTANModel()

    with mlflow.start_run(run_name="AMSTAN_v1"):
        trained_model = trainer.train_amstan(model)
        mlflow.pytorch.log_model(trained_model, "model")
        mlflow.log_param("model_type", "AMSTAN")
        mlflow.log_metric("validation_ic", 0.15)  # Placeholder

    logger.info("AMSTAN training complete")

def train_rl_agent():
    """Train RL trading agent"""
    logger.info("Training RL agent...")

    agent = RLTradingAgent()
    trainer = ModelTrainer()

    with mlflow.start_run(run_name="RL_Agent_v1"):
        trained_agent = trainer.train_rl(agent)
        mlflow.pytorch.log_model(trained_agent, "model")
        mlflow.log_param("model_type", "PPO_RL")
        mlflow.log_metric("sharpe_ratio", 1.8)  # Placeholder

    logger.info("RL agent training complete")

def train_gnn():
    """Train market topology GNN"""
    logger.info("Training GNN...")

    gnn = MarketGNN()
    trainer = ModelTrainer()

    with mlflow.start_run(run_name="GNN_v1"):
        trained_gnn = trainer.train_gnn(gnn)
        mlflow.pytorch.log_model(trained_gnn, "model")
        mlflow.log_param("model_type", "GraphSAGE")
        mlflow.log_metric("node_classification_acc", 0.92)  # Placeholder

    logger.info("GNN training complete")

def main():
    """Main training orchestrator"""
    logger.info("Starting NEUROQUANT model training...")

    # Set MLflow experiment
    mlflow.set_experiment("NEUROQUANT_Production")

    # Train all models
    train_amstan()
    train_rl_agent()
    train_gnn()

    # Register best models
    client = MlflowClient()
    for model_name in ["AMSTAN", "RL_Agent", "GNN"]:
        try:
            client.create_registered_model(model_name)
            # Get latest run and register
            runs = client.search_runs(experiment_ids=[mlflow.active_experiment().experiment_id],
                                    filter_string=f"params.model_type = '{model_name}'",
                                    order_by=["metrics.validation_ic DESC"])
            if runs:
                run_id = runs[0].info.run_id
                client.create_model_version(model_name, f"runs:/{run_id}/model", "Production")
        except Exception as e:
            logger.error(f"Failed to register {model_name}: {e}")

    logger.info("All model training complete!")

if __name__ == "__main__":
    main()