import re

with open("app/services/prediction_engine.py", "r") as f:
    code = f.read()

# Replace the heuristic block
pattern = re.compile(r'    # EXPLICIT FUSION RULE \(Phase A6\).*?raw_ensemble = float\(np\.clip\(fused_score, -1\.0, 1\.0\)\)', re.DOTALL)

replacement = """    # METALEARNER ENSEMBLE COMBINING
    tech_score = 0.0 # TechnicalSignalEngine is eradicated
    
    # FinBERT sentiment
    sentiment_score = 0.0
    try:
        from app.services.sentiment_analyzer import FinBERTSentimentAnalyzer
        analyzer = FinBERTSentimentAnalyzer()
        if getattr(analyzer, "_initialized", False) or getattr(analyzer, "vader", None):
            headlines = analyzer.scrape_google_news(f"{symbol} stock India")
            if headlines:
                sentiment_score = analyzer.get_stock_sentiment(symbol, headlines)
    except Exception as e:
        logger.warning(f"FinBERT sentiment extraction failed: {e}")

    ml_score = xgb_score if xgb_status == "trained" else 0.0

    try:
        from research.models.ensemble.meta_learner import EnsembleMetaLearner
        meta_learner = EnsembleMetaLearner.load()
        if meta_learner:
            # Requires OOF predictions: XGB, LSTM, TFT, HMM, etc.
            scores = [
                model_signals.get("xgboost", 0.0),
                model_signals.get("lstm_attention", 0.0),
                model_signals.get("tft", 0.0),
                model_signals.get("hmm_garch", 0.0),
                model_signals.get("gnn", 0.0),
                sentiment_score
            ]
            prob_up = meta_learner.predict_proba(scores)
            raw_ensemble = float((prob_up - 0.5) * 2.0)
        else:
            raise ValueError("No meta_learner loaded")
    except Exception as e:
        # Fallback if meta-learner is untrained/missing
        fused_score = (0.7 * ml_score) + (0.3 * (model_signals.get("tft") or 0.0)) + (0.1 * sentiment_score)
        
        regime = regime_info.get("regime", "NEUTRAL")
        if regime in ("BEAR", "CRISIS") and fused_score > 0:
            fused_score = min(fused_score, 0.2)
        elif regime == "BULL" and fused_score < 0:
            fused_score = max(fused_score, -0.2)

        raw_ensemble = float(np.clip(fused_score, -1.0, 1.0))"""

if pattern.search(code):
    print("Found fusion logic, replacing...")
    new_code = pattern.sub(replacement, code)
    with open("app/services/prediction_engine.py", "w") as f:
        f.write(new_code)
else:
    print("Fusion logic not found!")
