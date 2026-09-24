import re

with open('tests/unit/test_intelligence_service_new.py', 'r') as f:
    text = f.read()

text = re.sub(r'def test_([a-zA-Z0-9_]+)\(', r'@pytest.mark.asyncio\nasync def test_\1(', text)
text = text.replace("@pytest.mark.asyncio\n@pytest.mark.asyncio", "@pytest.mark.asyncio")

# Change service.get_ to await service.get_
text = re.sub(r'service\.get_([a-zA-Z0-9_]+)\(', r'await service.get_\1(', text)
text = text.replace("await await", "await")

# Add import pytest if missing
if 'import pytest' not in text:
    text = 'import pytest\n' + text

with open('tests/unit/test_intelligence_service_new.py', 'w') as f:
    f.write(text)
