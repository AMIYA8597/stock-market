import asyncio
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.basicConfig(level=logging.WARNING, format="%(message)s")

from app.services.prediction_engine import get_full_prediction


async def prove_shap():
    print("--- PROVING SHAP ADDITIVITY ---")
    symbol = "RELIANCE.NS"
    print(f"Fetching full prediction for {symbol} (bypassing cache)...")

    # We pass bypass_cache=True to ensure it runs the real model inference
    pred = await get_full_prediction(symbol, bypass_cache=True)

    ensemble = pred.get("ensemble", {})
    xgb_data = ensemble.get("xgboost", {})
    if xgb_data.get("status") != "trained":
        print("XGBoost model not trained or available. Please train it first.")
        return

    xgb_score = xgb_data["xgb_score"]
    base_value = xgb_data.get("base_value", 0.0)
    top_features = xgb_data.get("top_features", [])

    print("Model Output Margin (xgb_score / 2 to get raw margin? Wait, prediction engine does xgb_score = (prob_up - 0.5)*2.0)")

    # xgb_score is mapped. Let's look at raw SHAP sum.
    # SHAP additivity: sum(SHAP) + base_value = margin output in log-odds space (for trees) or probability space?
    # Usually for xgboost, it's log-odds (margin).

    total_shap = sum(f["shap_value"] for f in top_features)

    print(f"Base Value: {base_value:.4f}")
    print(f"Total SHAP Contribution (top 10): {total_shap:.4f}")
    print(f"Base + SHAP: {(base_value + total_shap):.4f}")

    # For binary classification with logloss, the model output margin is usually what SHAP sums to.
    print(f"Engine's Extracted XGB Score: {xgb_score:.4f}")
    print(f"Note: top_features only includes the top K, so the sum might not perfectly equal the margin if K < total_features. Let's count features: {len(top_features)}")

    # We will also load the model directly to prove full additivity
    from pathlib import Path

    import pandas as pd

    from research.models.xgboost_model.classifier import XGBoostDirectionalClassifier

    model_path = Path(__file__).parent.parent / "data" / "models" / f"xgboost_{symbol.upper()}.pkl"
    if model_path.exists():
        clf = XGBoostDirectionalClassifier.load(model_path)
        from datetime import UTC, datetime, timedelta

        from app.services.data_ingestion.provider_manager import provider_manager

        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=60)
        bars = await provider_manager.get_ohlcv(symbol, "1d", start_date, end_date)
        df = pd.DataFrame([{
            "time": b.time.replace(tzinfo=None) if b.time.tzinfo else b.time,
            "open": b.open, "high": b.high, "low": b.low, "close": b.close, "volume": b.volume
        } for b in bars])

        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from research.feature_engineering.pipeline import FeaturePipeline
        df = FeaturePipeline().run(df)
        df.ta.rsi(length=14, append=True)
        # We just need any valid row to pass to get_shap_values

        # We will manually get full SHAP explanation
        from research.explainability.shap_explainer import get_tree_shap
        x_dict = {f: float(df[f].iloc[-1]) if f in df.columns else 0.0 for f in clf.features}
        import numpy as np
        X = np.array([list(x_dict.values())])
        base_estimator = clf.model.estimator if hasattr(clf.model, "estimator") else clf.model
        expl = get_tree_shap(base_estimator, X, clf.features)

        full_shap_sum = float(np.sum(expl.values[0]))
        full_base = expl.base_value
        print("\n--- Full Matrix Additivity Check ---")
        print(f"Full SHAP Sum ({len(clf.features)} features): {full_shap_sum:.4f}")
        print(f"Base Value: {full_base:.4f}")
        total_margin = full_shap_sum + full_base
        print(f"Sum + Base = {total_margin:.4f}")

        # XGBoost output margin
        margin = base_estimator.predict(X, output_margin=True)[0]
        print(f"Actual XGBoost Output Margin: {margin:.4f}")
        if abs(total_margin - margin) < 1e-4:
            print("SHAP ADDITIVITY VERIFIED! The values perfectly sum to the model margin.")
        else:
            print("Mismatch in SHAP additivity.")

asyncio.run(prove_shap())
