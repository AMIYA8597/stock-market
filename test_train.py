import asyncio
import logging
import os
import sys
import yfinance as yf
import pandas as pd

# Setup path to import backend
sys.path.append(os.path.abspath('backend'))

from app.services.ml_engine.training_pipeline import TrainingPipeline

async def train_model():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    print("Downloading historical data for RELIANCE.NS for ML training...")
    # Get plenty of data for ML training
    df = yf.download("RELIANCE.NS", period="5y", interval="1d")
    
    # Flatten columns if MultiIndex
    if hasattr(df.columns, 'droplevel'): 
        df.columns = df.columns.droplevel(1)
        
    df.reset_index(inplace=True)
    df.rename(columns={c: str(c).lower() for c in df.columns}, inplace=True)
    
    if 'date' in df.columns:
        df.rename(columns={'date': 'time'}, inplace=True)
    elif 'datetime' in df.columns:
        df.rename(columns={'datetime': 'time'}, inplace=True)
    
    pipeline = TrainingPipeline("RELIANCE.NS")
    
    print("Starting ML Pipeline...")
    results = await pipeline.run(frame=df)
    
    print("\n--- TRAINING COMPLETE ---")
    print(f"RandomForest Test Acc: {results['random_forest']['accuracy']:.4f}")
    print(f"XGBoost Test Acc:      {results['xgboost']['accuracy']:.4f}")
    print(f"LightGBM Test Acc:     {results['lightgbm']['accuracy']:.4f}")
    print(f"Best Model Selected:   {results['best_model']}")

if __name__ == "__main__":
    asyncio.run(train_model())
