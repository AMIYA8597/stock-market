import asyncio
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.v1.explain import get_shap_explanation
from app.api.v1.predictions import get_prediction
from app.database.connection import async_session_factory


async def main():
    async with async_session_factory() as db:
        print("--- Testing /api/v1/predictions/RELIANCE ---")
        try:
            pred = await get_prediction("RELIANCE.NS", db)
            ens = pred.get("ensemble", {})
            print(f"Status: {ens.get('model_status')}")
            print(f"Direction: {ens.get('direction')}")
            print(f"Confidence: {ens.get('confidence')}")
            print(f"Expected Move: {ens.get('expected_move_range')}")
            print(f"Regime: {ens.get('regime', {}).get('regime')}")
            print(f"XGBoost Status: {ens.get('xgboost', {}).get('status')}")
            print(f"Raw Ensemble: {ens.get('raw_ensemble')}")
        except Exception as e:
            print(f"Exception in prediction: {e}")

        print("\n--- Testing /api/v1/explain/shap/RELIANCE ---")
        try:
            shap_resp = await get_shap_explanation("RELIANCE.NS")
            print(f"Base Value: {shap_resp.base_value}")
            print(f"Output Value: {shap_resp.output_value}")
            if shap_resp.feature_contributions:
                print(f"Top Feature: {shap_resp.feature_contributions[0].name} = {shap_resp.feature_contributions[0].shap_value}")
            else:
                print("No feature contributions.")
        except Exception as e:
            print(f"Exception in shap: {e}")

if __name__ == "__main__":
    asyncio.run(main())
