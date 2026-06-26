import sys
import pathlib
import os

# Add backend directory to path
project_root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from research.models.ensemble.meta_learner import EnsembleMetaLearner

def main():
    symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"]
    learner = EnsembleMetaLearner()
    
    print("Preparing training data (this may take a minute as it runs walk-forward simulation)...")
    X, y = learner.prepare_training_data(symbols)
    print(f"Data prepared. Samples: {len(X)}")
    
    if X.empty:
        print("Error: No training data generated.")
        return
        
    print("Training meta-models...")
    metrics = learner.train(X, y)
    print("Training complete. Metrics:")
    print(f"  Old Fixed-Weight Brier: {metrics['old_fixed_brier']:.6f}")
    print(f"  Logistic Meta Brier:    {metrics['logistic_brier']:.6f}")
    print(f"  LightGBM Meta Brier:    {metrics['lightgbm_brier']:.6f}")
    print(f"  Winner: {metrics['best_model']}")
    
    learner.save()
    print("Model serialized successfully.")

if __name__ == "__main__":
    main()
