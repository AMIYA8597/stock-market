import re

path = r"d:\work\stock-market\backend\app\services\prediction_engine.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# 1. Patch XGBoost block
xgb_find = """            if xgb_clf is not None and xgb_clf.model is not None:
                prob_up = xgb_clf.predict_proba(df)
                xgb_score = float((prob_up - 0.5) * 2.0)
                xgb_confidence = float(prob_up if prob_up > 0.5 else (1.0 - prob_up))
                xgb_top_features = xgb_clf.get_feature_importances()
                xgb_status = "trained" """
xgb_repl = """            if xgb_clf is not None:
                # Determine raw model vs wrapper
                if hasattr(xgb_clf, "model"):
                    base_estimator = xgb_clf.model
                    features = getattr(xgb_clf, "features", list(df.columns))
                    scaler = getattr(xgb_clf, "scaler", None)
                    prob_up_array = xgb_clf.predict_proba(df)
                else:
                    base_estimator = xgb_clf
                    if hasattr(base_estimator, "estimator"):
                        actual = base_estimator.estimator
                    elif hasattr(base_estimator, "calibrated_classifiers_"):
                        actual = base_estimator.calibrated_classifiers_[0].estimator
                    else:
                        actual = base_estimator

                    features = getattr(actual, "feature_names_in_", None)
                    if features is None:
                        features = [c for c in df.columns if df[c].dtype in ['float64', 'float32', 'int64', 'int32']]
                    scaler = None
                    x_clean = df[[f for f in features if f in df.columns]]
                    if hasattr(xgb_clf, "scaler") and xgb_clf.scaler is not None:
                        x_clean = xgb_clf.scaler.transform(x_clean)
                    prob_up_array = xgb_clf.predict_proba(x_clean)

                if base_estimator is not None:
                    prob_up = prob_up_array[1] if isinstance(prob_up_array, (list, tuple, np.ndarray)) and len(prob_up_array) > 1 else prob_up_array
                    if isinstance(prob_up, np.ndarray):
                        prob_up = float(prob_up[-1])
                    xgb_score = float((prob_up - 0.5) * 2.0)
                    xgb_confidence = float(prob_up if prob_up > 0.5 else (1.0 - prob_up))

                    # SHAP EXPLAINER
                    try:
                        from research.explainability.shap_explainer import get_tree_shap, top_contributors
                        last_row_df = df[[f for f in features if f in df.columns]].iloc[-1:]
                        if hasattr(base_estimator, "estimator"):
                            actual_model = base_estimator.estimator
                        elif hasattr(base_estimator, "calibrated_classifiers_"):
                            actual_model = base_estimator.calibrated_classifiers_[0].estimator
                        else:
                            actual_model = base_estimator

                        if scaler is not None:
                            x_scaled = scaler.transform(last_row_df.values)
                        else:
                            x_scaled = last_row_df.values

                        shap_expl = get_tree_shap(actual_model, x_scaled, feature_names=features)
                        xgb_top_features = [{"name": name, "importance": val} for name, val in top_contributors(shap_expl, 0, top_k=15)]
                        xgb_base_value = float(shap_expl.base_value)
                    except Exception as shap_err:
                        import logging
                        logging.warning(f"Failed to extract true SHAP: {shap_err}. Falling back.")
                        if hasattr(xgb_clf, "get_feature_importances"):
                            xgb_top_features = [{"name": f["name"], "importance": f["importance"]} for f in xgb_clf.get_feature_importances()]
                        else:
                            xgb_top_features = []
                        xgb_base_value = 0.5

                    xgb_status = "trained" """
content = content.replace(xgb_find, xgb_repl)

# 2. Patch Fusion Rule block
pattern = r"    # 3\. Dynamic Weight Management and Ensemble Combining.*?    # 4\. Sizing and Stops"
fusion_repl = """    # 3. Dynamic Weight Management and Ensemble Combining
    # EXPLICIT FUSION RULE (Phase A6)
    # final = (0.4 * technical) + (0.6 * ML) + sentiment_tilt + regime_gate

    technical = TechnicalSignalEngine.generate_signal(df)
    tech_score = technical["score"]

    # simulated lookahead-free sentiment score
    import datetime
    import numpy as np
    ret_5d = float((df["close"].iloc[-1] / df["close"].iloc[max(0, len(df)-6)]) - 1.0) if len(df) >= 6 else 0.0
    dt_str = str(df["time"].iloc[-1]) if "time" in df.columns else str(datetime.datetime.now().date())
    noise_val = (((sum(ord(c) for c in dt_str) + sum(ord(c) for c in symbol)) % 100) / 500.0) - 0.1
    sentiment_score = float(np.clip(1.5 * ret_5d + noise_val, -1.0, 1.0))
    sentiment_tilt = sentiment_score * 0.15

    ml_score = xgb_score if xgb_status == "trained" else 0.0

    fused_score = (0.4 * tech_score) + (0.6 * ml_score) + sentiment_tilt

    regime = regime_info["regime"]
    if regime in ("BEAR", "CRISIS") and fused_score > 0:
        fused_score = min(fused_score, 0.2)  # Suppress BUY
    elif regime == "BULL" and fused_score < 0:
        fused_score = max(fused_score, -0.2) # Suppress SELL

    raw_ensemble = float(np.clip(fused_score, -1.0, 1.0))
    prob_up = (raw_ensemble / 2.0) + 0.5
    ensemble_confidence = float(prob_up if prob_up > 0.5 else (1.0 - prob_up))

    active_signals = [xgb_score] if xgb_status == "trained" else [tech_score]
    if len(active_signals) > 0:
        pos = sum(1 for s in active_signals if s > 0.1)
        neg = sum(1 for s in active_signals if s < -0.1)
        total_votes = pos + neg
        agreement = max(pos, neg) / total_votes if total_votes > 0 else 0.5
    else:
        agreement = 0.5

    # 4. Sizing and Stops"""

content = re.sub(pattern, fusion_repl, content, flags=re.DOTALL)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
