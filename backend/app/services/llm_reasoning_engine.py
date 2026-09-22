import json
import os
from typing import Any

import httpx
from loguru import logger


class LLMReasoningEngine:
    """
    Phase 9: LLM Reasoning Engine
    Uses the Gemini API to provide human-readable, AI-driven explanations and
    confidence bounds based on deep learning model outputs, market context, and
    technicals.
    """

    @staticmethod
    async def generate_reasoning(
        symbol: str,
        ensemble_signal: str,
        confidence: float,
        technicals: dict[str, Any],
        news_sentiment: str
    ) -> str:
        """
        Generates an actionable reasoning string.
        Gracefully falls back to heuristic reasoning if the API key is missing.
        """

        gemini_key = os.getenv("GEMINI_API_KEY")

        prompt = f"""
        You are an institutional quantitative trading AI.
        Generate a strictly concise, 1-sentence reasoning for the following signal.
        Symbol: {symbol}
        Signal: {ensemble_signal} (Confidence: {confidence}%)
        Sentiment: {news_sentiment}
        Technicals: {json.dumps(technicals)}
        """

        try:
            if gemini_key:
                return await LLMReasoningEngine._call_gemini(prompt, gemini_key)
            return LLMReasoningEngine._heuristic_fallback(ensemble_signal, technicals, news_sentiment)
        except Exception as e:
            logger.error(f"LLM Reasoning failed: {e}")
            return LLMReasoningEngine._heuristic_fallback(ensemble_signal, technicals, news_sentiment)

    @staticmethod
    async def _call_gemini(prompt: str, key: str) -> str:
        async with httpx.AsyncClient() as client:
            model = os.getenv("GEMINI_MODEL")
            if not model:
                raise ValueError("GEMINI_MODEL is required")
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                json={"contents": [{"parts": [{"text": prompt}]}]},
                headers={"x-goog-api-key": key},
                timeout=10.0
            )
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    @staticmethod
    def _heuristic_fallback(signal: str, technicals: dict[str, Any], sentiment: str) -> str:
        rsi = technicals.get("RSI_14")
        if rsi is None:
            return f"Ensemble indicates {signal}; technical RSI data is unavailable."
        rsi_msg = "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral"
        return f"Ensemble indicates {signal} with {sentiment} market sentiment and {rsi_msg} RSI momentum."

