
path = r"d:\work\stock-market\backend\app\services\prediction_engine.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# Revert SHAP logic in prediction_engine.py back to get_feature_importances()
shap_block = """                    # SHAP EXPLAINER
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
                        xgb_base_value = 0.5"""

fast_block = """                    if hasattr(xgb_clf, "get_feature_importances"):
                        xgb_top_features = [{"name": f["name"], "importance": f["importance"]} for f in xgb_clf.get_feature_importances()]
                    else:
                        xgb_top_features = []
                    xgb_base_value = 0.5"""

content = content.replace(shap_block, fast_block)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
