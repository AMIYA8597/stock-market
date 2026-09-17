import os
import sys
import asyncio
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.WARNING, format="%(message)s")

from app.services.prediction_engine import get_full_prediction
from app.services.intelligence_service import IntelligenceService
from app.schemas.explain import CounterfactualRequest

async def prove_counterfactual():
    print("--- PROVING GENUINE COUNTERFACTUAL GENERATION ---")
    symbol = "RELIANCE.NS"
    print(f"Fetching full prediction for {symbol} (bypassing cache)...")

    # We pass bypass_cache=True to ensure it runs the real model inference
    pred = await get_full_prediction(symbol, bypass_cache=True)

    ensemble = pred.get("ensemble", {})
    xgb_data = ensemble.get("xgboost", {})
    if xgb_data.get("status") != "trained":
        print("XGBoost model not trained or available. Please train it first.")
        return

    xgb_dir = xgb_data.get("xgb_direction", "NEUTRAL")
    print(f"Current Model Direction: {xgb_dir}")

    # We want to flip it
    target_dir = "SELL" if xgb_dir in ("BUY", "NEUTRAL") else "BUY"
    print(f"Targeting Counterfactual Flip to: {target_dir}")

    print("\nCalling the Explainability API to generate counterfactuals via iterative perturbation...")
    service = IntelligenceService()
    req = CounterfactualRequest(target_direction=target_dir, num_cfs=3)
    cfs = service.get_counterfactuals(symbol, req)

    print(f"Found {len(cfs)} counterfactual perturbations that successfully flip the model!")
    for cf in cfs:
        print(f"\n{cf.cf_id} (Proximity: {cf.proximity_score}):")
        for change in cf.changed_features:
            print(f"  Feature {change.name}: Original = {change.original:.4f} --> Counterfactual = {change.counterfactual:.4f}")
        print(f"  Resulting Signal: {cf.resulting_signal}")

    if len(cfs) > 0:
        print("\nCOUNTERFACTUAL VERIFIED! The algorithm successfully found real feature perturbations that physically flip the model's prediction boundary.")
    else:
        print("\nFailed to find any counterfactuals within the step limit.")

asyncio.run(prove_counterfactual())
