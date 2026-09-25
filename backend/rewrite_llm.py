import re

with open('d:/work/stock-market/backend/app/services/llm_reasoning_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_sig = '''    @staticmethod
    async def generate_reasoning(
        symbol: str,
        ensemble_signal: str,
        confidence: float,
        technicals: dict[str, Any],
        news_sentiment: str
    ) -> str:'''

new_sig = '''    @staticmethod
    async def generate_reasoning(
        evidence_pack: dict[str, Any]
    ) -> str:'''

text = text.replace(old_sig, new_sig)

old_prompt = '''        prompt = f"""
        You are an institutional quantitative trading AI.
        Generate a strictly concise, 1-sentence reasoning for the following signal.
        DO NOT invent, synthesize, or output any numerical performance records, accuracy scores, or price targets that are not explicitly provided below.
        
        Context:
        Symbol: {symbol}
        Signal: {ensemble_signal} (Confidence: {confidence})
        Sentiment: {news_sentiment}
        Technicals: {json.dumps(technicals)}
        """'''

new_prompt = '''        prompt = f"""
        You are an institutional quantitative trading AI.
        Generate a strictly concise, 1-sentence reasoning for the following signal based ONLY on the evidence pack.
        DO NOT invent, synthesize, or output any numerical performance records, accuracy scores, or price targets that are not explicitly provided below.
        
        Evidence Pack:
        {json.dumps(evidence_pack, indent=2)}
        """'''
        
text = text.replace(old_prompt, new_prompt)

old_call = '''        provider = LLMReasoningEngine.get_provider()
        if not provider:
            return LLMReasoningEngine._heuristic_fallback(ensemble_signal, technicals, news_sentiment)

        try:
            raw_text = await provider.generate_text(prompt)
            evidence = {
                "signal": ensemble_signal,
                "confidence": confidence,
                "technicals": technicals,
                "sentiment": news_sentiment
            }
            return LLMReasoningEngine._validate_numeric_claims(raw_text, evidence)
        except Exception as e:
            logger.error(f"LLM Reasoning failed: {e}")
            return LLMReasoningEngine._heuristic_fallback(ensemble_signal, technicals, news_sentiment)'''

new_call = '''        provider = LLMReasoningEngine.get_provider()
        if not provider:
            return LLMReasoningEngine._heuristic_fallback(evidence_pack)

        try:
            raw_text = await provider.generate_text(prompt)
            return LLMReasoningEngine._validate_numeric_claims(raw_text, evidence_pack)
        except Exception as e:
            logger.error(f"LLM Reasoning failed: {e}")
            return LLMReasoningEngine._heuristic_fallback(evidence_pack)'''

text = text.replace(old_call, new_call)

old_fallback = '''    @staticmethod
    def _heuristic_fallback(signal: str, technicals: dict[str, Any], sentiment: str) -> str:
        rsi = technicals.get("RSI_14")
        if rsi is None:
            return f"Ensemble indicates {signal}; technical RSI data is unavailable."
        rsi_msg = "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral"
        return f"Ensemble indicates {signal} with {sentiment} market sentiment and {rsi_msg} RSI momentum."'''

new_fallback = '''    @staticmethod
    def _heuristic_fallback(evidence: dict) -> str:
        signal = evidence.get("signal", "HOLD")
        technicals = evidence.get("technicals", {})
        sentiment = evidence.get("sentiment", "neutral")
        rsi = technicals.get("RSI_14")
        if rsi is None:
            return f"Ensemble indicates {signal}; technical RSI data is unavailable."
        rsi_msg = "oversold" if float(rsi) < 30 else "overbought" if float(rsi) > 70 else "neutral"
        return f"Ensemble indicates {signal} with {sentiment} market sentiment and {rsi_msg} RSI momentum."'''

text = text.replace(old_fallback, new_fallback)

# Also fix evidence["signal"] in _validate_numeric_claims
text = text.replace('evidence["signal"], evidence["technicals"], evidence["sentiment"]', 'evidence')

with open('d:/work/stock-market/backend/app/services/llm_reasoning_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
