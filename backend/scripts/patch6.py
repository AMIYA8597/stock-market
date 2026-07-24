
path = r"d:\work\stock-market\backend\app\services\prediction_engine.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# Add masked_weights back
missing = """    active_signals = [xgb_score] if xgb_status == "trained" else [tech_score]
    if len(active_signals) > 0:
        pos = sum(1 for s in active_signals if s > 0.1)
        neg = sum(1 for s in active_signals if s < -0.1)
        total_votes = pos + neg
        agreement = max(pos, neg) / total_votes if total_votes > 0 else 0.5
    else:
        agreement = 0.5

    masked_weights = [1.0 if m == "xgboost" else 0.0 for m in model_names]

    # 4. Sizing and Stops"""

content = content.replace("""    active_signals = [xgb_score] if xgb_status == "trained" else [tech_score]
    if len(active_signals) > 0:
        pos = sum(1 for s in active_signals if s > 0.1)
        neg = sum(1 for s in active_signals if s < -0.1)
        total_votes = pos + neg
        agreement = max(pos, neg) / total_votes if total_votes > 0 else 0.5
    else:
        agreement = 0.5

    # 4. Sizing and Stops""", missing)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
