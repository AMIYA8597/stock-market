import json
import os
from typing import Any

import httpx
from loguru import logger


class LLMReasoningEngine:
    """
    Phase 9: LLM Reasoning Engine
    Uses OpenAI, Claude, or Gemini APIs to provide human-readable, AI-driven explanations
    and confidence bounds based on deep learning model outputs, market context, and technicals.
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
        Gracefully falls back to heuristic reasoning if API keys are missing.
        """
        openai_key = os.getenv("OPENAI_API_KEY")
        claude_key = os.getenv("CLAUDE_API_KEY")
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
            if openai_key:
                return await LLMReasoningEngine._call_openai(prompt, openai_key)
            elif claude_key:
                return await LLMReasoningEngine._call_claude(prompt, claude_key)
            elif gemini_key:
                return await LLMReasoningEngine._call_gemini(prompt, gemini_key)
            else:
                return LLMReasoningEngine._heuristic_fallback(ensemble_signal, technicals, news_sentiment)
        except Exception as e:
            logger.error(f"LLM Reasoning failed: {e}")
            return LLMReasoningEngine._heuristic_fallback(ensemble_signal, technicals, news_sentiment)

    @staticmethod
    async def _call_openai(prompt: str, key: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 100
                },
                timeout=10.0
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

    @staticmethod
    async def _call_claude(prompt: str, key: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                json={
                    "model": "claude-3-5-sonnet-20241022",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 100
                },
                timeout=10.0
            )
            resp.raise_for_status()
            data = resp.json()
            return data["content"][0]["text"].strip()

    @staticmethod
    async def _call_gemini(prompt: str, key: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=10.0
            )
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    @staticmethod
    def _heuristic_fallback(signal: str, technicals: dict[str, Any], sentiment: str) -> str:
        rsi = technicals.get("RSI_14", 50)
        rsi_msg = "oversold" if rsi < 30 else "overbought" if rsi > 70 else "neutral"
        return f"Ensemble indicates {signal} with {sentiment} market sentiment and {rsi_msg} RSI momentum."

