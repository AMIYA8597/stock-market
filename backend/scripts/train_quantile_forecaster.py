import sys
import pathlib
import os

# Add backend directory to path
project_root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from research.models.tft.quantile_forecaster import QuantileLGBForecaster

def main():
    symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"]
    forecaster = QuantileLGBForecaster()
    
    print("Preparing training data for Quantile LightGBM Forecaster...")
    X, y = forecaster.prepare_training_data(symbols)
    print(f"Data prepared. Samples: {len(X)}")
    
    if X.empty:
        print("Error: No training data generated.")
        return
        
    print("Training quantile models (P10, P50, P90)...")
    forecaster.train(X, y)
    print("Training complete. Serializing models...")
    forecaster.save()
    print("Quantile LGB models saved successfully.")

if __name__ == "__main__":
    main()
