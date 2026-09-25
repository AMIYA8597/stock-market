import json
import os
import httpx
from typing import Any, Protocol, Optional
from loguru import logger

class LLMProvider(Protocol):
    async def generate_text(self, prompt: str) -> str:
        ...

class GeminiProvider:
    def __init__(self, key: str, model: str):
        self.key = key
        self.model = model

    async def generate_text(self, prompt: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                json={"contents": [{"parts": [{"text": prompt}]}]},
                headers={"x-goog-api-key": self.key},
                timeout=10.0
            )
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()

class GroqProvider:
    def __init__(self, key: str, model: str):
        self.key = key
        self.model = model

    async def generate_text(self, prompt: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0
                },
                headers={"Authorization": f"Bearer {self.key}"},
                timeout=10.0
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()



class OllamaProvider:
    def __init__(self, host: str, model: str):
        self.host = host
        self.model = model

    async def generate_text(self, prompt: str) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=20.0
            )
            resp.raise_for_status()
            data = resp.json()
            return data["response"].strip()

class LLMReasoningEngine:
    @staticmethod
    def get_provider() -> Optional[LLMProvider]:
        # Prefer Groq, then Gemini, then fallback
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            return GroqProvider(groq_key, os.getenv("GROQ_MODEL", "llama3-8b-8192"))
            
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            return GeminiProvider(gemini_key, os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
            
        ollama_host = os.getenv("OLLAMA_HOST")
        if ollama_host:
            return OllamaProvider(ollama_host, os.getenv("OLLAMA_MODEL", "llama3"))
            
        return None

    @staticmethod
    async def generate_reasoning(
        evidence_pack: dict[str, Any]
    ) -> str:
        prompt = f"""
        You are an institutional quantitative trading AI.
        Generate a strictly concise, 1-sentence reasoning for the following signal based ONLY on the evidence pack.
        DO NOT invent, synthesize, or output any numerical performance records, accuracy scores, or price targets that are not explicitly provided below.
        
        Evidence Pack:
        {json.dumps(evidence_pack, indent=2)}
        """

        provider = LLMReasoningEngine.get_provider()
        if not provider:
            return LLMReasoningEngine._heuristic_fallback(evidence_pack)

        try:
            raw_text = await provider.generate_text(prompt)
            return LLMReasoningEngine._validate_numeric_claims(raw_text, evidence_pack)
        except Exception as e:
            logger.error(f"LLM Reasoning failed: {e}")
            return LLMReasoningEngine._heuristic_fallback(evidence_pack)


    @staticmethod
    def _validate_numeric_claims(text: str, evidence: dict) -> str:
        '''Enforces V2-25: LLM NEVER OWNS THE NUMBERS.'''
        import re
        
        # Extract all numbers from the text
        numbers = re.findall(r'-?\d+\.?\d*', text)
        
        # Extract all numbers from the evidence
        evidence_str = str(evidence)
        evidence_numbers = re.findall(r'-?\d+\.?\d*', evidence_str)
        
        # Check if any number in the text is NOT in the evidence
        for num_str in numbers:
            try:
                num = float(num_str)
                found = False
                for ev_num_str in evidence_numbers:
                    try:
                        if abs(num - float(ev_num_str)) < 0.001:
                            found = True
                            break
                    except:
                        pass
                
                # Allow common small integers like 14-day RSI
                if not found and num not in [0.0, 1.0, 14.0]:
                    logger.warning(f"LLM hallucinated number {num}. Stripping numerical claims.")
                    return LLMReasoningEngine._heuristic_fallback(evidence)
            except:
                pass
                
        return text

    @staticmethod
    def _heuristic_fallback(evidence: dict) -> str:
        signal = evidence.get("signal", "HOLD")
        technicals = evidence.get("technicals", {})
        sentiment = evidence.get("sentiment", "neutral")
        rsi = technicals.get("RSI_14")
        if rsi is None:
            return f"Ensemble indicates {signal}; technical RSI data is unavailable."
        rsi_msg = "oversold" if float(rsi) < 30 else "overbought" if float(rsi) > 70 else "neutral"
        return f"Ensemble indicates {signal} with {sentiment} market sentiment and {rsi_msg} RSI momentum."
