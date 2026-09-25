import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from app.database.connection import async_session_factory
from app.models.instrument import Instrument
from app.models.research import ModelRegistry as ModelArtifact
from app.services.prediction_engine import get_full_prediction


async def run_trace():
    print("=== TASK 1: END-TO-END PREDICTION TRACE ===")

    symbol = "RELIANCE.NS"
    # Find artifact
    async with async_session_factory() as session:
        stmt = (
            select(ModelArtifact)
            .join(Instrument)
            .where(Instrument.symbol == "RELIANCE.NS", ModelArtifact.is_active)
        )
        result = await session.execute(stmt)
        artifact = result.scalar_one_or_none()

        artifact_path = artifact.artifact_path if artifact else None
        version = artifact.version_tag if artifact else None

    if not artifact:
        print(f"Warning: No active model artifact found for {symbol} in DB. Engine will use heuristic/fallback unless file exists.")

    print(f"Executing get_full_prediction for {symbol} with bypass_cache=True...")
    res = await get_full_prediction(symbol, bypass_cache=True, artifact_path=artifact_path, model_version=version)

    print("\n--- HMM REGIME DETECTION ---")
    regime_info = res["ensemble"]["regime"]
    print(f"Regime State: {regime_info['regime']}")
    print(f"HMM Used: {regime_info['hmm_used']}")
    print(f"Regime Confidence: {regime_info['regime_confidence']:.2%}")
    print(f"Conditional Volatility: {regime_info['conditional_vol']:.4f}")

    print("\n--- XGBOOST OUTPUT ---")
    xgb = res["ensemble"]["xgboost"]
    print(f"XGBoost Status: {xgb['status']}")
    print(f"Raw Signal Score: {xgb['xgb_score']:.4f}")
    print(f"Confidence: {xgb['xgb_confidence']:.2%}")
    print(f"XGBoost Direction: {xgb['xgb_direction']}")

    print("\n--- FUSION RULE & FINAL ENSEMBLE ---")
    technical = res["ensemble"]["technical"]["score"]
    ml_score = xgb["xgb_score"] if xgb["status"] == "trained" else 0.0
    res.get("message", "")
    print(f"Technical Score: {technical:.4f}")
    print(f"ML Score: {ml_score:.4f}")
    print(f"Fused Raw Ensemble Score: {res['ensemble']['raw_ensemble']:.4f}")
    print(f"Final Direction: {res['ensemble']['direction']}")

    print("\n=== TASK 4: SHAP CONSISTENCY VERIFICATION ===")
    if xgb["status"] == "trained":
        base_val = xgb["base_value"]
        shap_sum = sum(feat["shap_value"] for feat in xgb["top_features"])
        reconstructed_margin = base_val + shap_sum

        # XGBoost output is margin. Probability = 1 / (1 + exp(-margin))
        import math
        reconstructed_prob = 1.0 / (1.0 + math.exp(-reconstructed_margin))
        reconstructed_score = (reconstructed_prob - 0.5) * 2.0

        print(f"Base Value: {base_val:.4f}")
        print(f"Sum of SHAP Values: {shap_sum:.4f}")
        print(f"Reconstructed Margin: {reconstructed_margin:.4f}")
        print(f"Reconstructed Score (approx): {reconstructed_score:.4f}")
        print(f"Actual XGBoost Score: {xgb['xgb_score']:.4f}")

        diff = abs(reconstructed_score - xgb['xgb_score'])
        if diff < 0.01:
            print("=> SHAP Consistency VERIFIED. The feature attributions sum to the model's actual output.")
        else:
            print("=> SHAP Consistency FAILED.")

    else:
        print("Model is not trained. Cannot perform SHAP verification.")

if __name__ == "__main__":
    asyncio.run(run_trace())
