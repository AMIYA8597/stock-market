import re

with open('backend/app/services/llm_reasoning_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove OpenAI and Claude
content = re.sub(
    r'openai_key = os\.getenv\("OPENAI_API_KEY"\)\s*claude_key = os\.getenv\("CLAUDE_API_KEY"\)',
    '',
    content
)

content = re.sub(
    r'if openai_key:\s*return await LLMReasoningEngine\._call_openai\(prompt, openai_key\)\s*elif claude_key:\s*return await LLMReasoningEngine\._call_claude\(prompt, claude_key\)\s*elif gemini_key:',
    'if gemini_key:',
    content
)

content = re.sub(
    r'    @staticmethod\s*async def _call_openai\(prompt: str, key: str\) -> str:.*?    @staticmethod\s*async def _call_claude\(prompt: str, key: str\) -> str:.*?    @staticmethod\s*async def _call_gemini',
    '    @staticmethod\n    async def _call_gemini',
    content,
    flags=re.DOTALL
)

with open('backend/app/services/llm_reasoning_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
