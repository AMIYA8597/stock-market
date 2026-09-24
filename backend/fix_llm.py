import re

with open("app/services/llm_reasoning_engine.py", "r") as f:
    code = f.read()

ollama_class = """
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

"""

if "class OllamaProvider:" not in code:
    code = code.replace("class LLMReasoningEngine:", ollama_class + "class LLMReasoningEngine:")

get_provider_logic = """    @staticmethod
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
            
        return None"""

code = re.sub(r'    @staticmethod\n    def get_provider\(\) -> Optional\[LLMProvider\]:.*?return None', get_provider_logic, code, flags=re.DOTALL)

with open("app/services/llm_reasoning_engine.py", "w") as f:
    f.write(code)
