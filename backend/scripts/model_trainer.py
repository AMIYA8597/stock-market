"""
Model training orchestration script.

Trains all ML models with walk-forward cross-validation,
logs experiments to MLflow, and saves best models to registry.

Usage:
    python scripts/model_trainer.py --model tft --symbol RELIANCE.NS
    python scripts/model_trainer.py --model all --universe nifty50

Fully implemented in Phase 3.
"""

from __future__ import annotations

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="QuantEdge Model Trainer")
    parser.add_argument(
        "--model", type=str, default="all",
        choices=["all", "tft", "cnn_bilstm", "xgboost_lgbm", "hmm", "finbert"],
    )
    parser.add_argument("--symbol", type=str, help="Single symbol to train on")
    parser.add_argument("--universe", type=str, help="Predefined universe")
    args = parser.parse_args()

    print("⚠️  Model trainer not yet implemented — coming in Phase 3")
    print(f"   Args: model={args.model}, symbol={args.symbol}, universe={args.universe}")
    sys.exit(0)


if __name__ == "__main__":
    main()
