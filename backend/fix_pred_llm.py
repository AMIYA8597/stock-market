
with open('d:/work/stock-market/backend/app/services/prediction_engine.py', encoding='utf-8') as f:
    text = f.read()

old_call = '''        # Run the LLM reasoning asynchronously
        llm_reason = await LLMReasoningEngine.generate_reasoning(
            symbol=symbol,
            ensemble_signal=ensemble.get("action", "HOLD"),
            confidence=float(ensemble.get("confidence", 50.0)),
            technicals=technicals_dict,
            news_sentiment="Neutral",  # In a real pass, fetch from sentiment_analyzer
        )'''

new_call = '''        # Run the LLM reasoning asynchronously
        evidence_pack = {
            "symbol": symbol,
            "signal": ensemble.get("action", "HOLD"),
            "confidence": float(ensemble.get("confidence", 50.0)),
            "technicals": technicals_dict,
            "sentiment": "Neutral"
        }
        llm_reason = await LLMReasoningEngine.generate_reasoning(evidence_pack=evidence_pack)'''

text = text.replace(old_call, new_call)

with open('d:/work/stock-market/backend/app/services/prediction_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
