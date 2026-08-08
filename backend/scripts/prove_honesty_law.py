import asyncio
import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

from app.services.ml_engine.training_pipeline import TrainingPipeline
from research.feature_engineering.pipeline import FeaturePipeline

async def test_honesty_law():
    print("--- PROVING HONESTY LAW ---")
    print("Injecting synthetic LEAKY feature into the feature pipeline...")
    
    original_run = FeaturePipeline.run
    
    def leaky_run(self, frame):
        # Run normal pipeline
        df = original_run(self, frame)
        # Inject exact future answer as a feature
        df["LEAKY_FUTURE_TARGET"] = df["target_direction"]
        return df
        
    FeaturePipeline.run = leaky_run
    
    print("Running TrainingPipeline on leaky data...")
    print("Expecting XGBoost/LightGBM to achieve ~100% accuracy and trigger Honesty Law Guard rejection.")
    
    pipeline = TrainingPipeline("RELIANCE.NS")
    try:
        await pipeline.run()
    except Exception as e:
        print(f"Pipeline error: {e}")

if __name__ == "__main__":
    asyncio.run(test_honesty_law())
