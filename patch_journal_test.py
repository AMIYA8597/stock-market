import re

with open('backend/tests/integration/test_api_journal.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r'from app\.core\.dependencies import get_current_user_or_none\s*async def override_get_current_user_or_none\(\):\s*return \{"sub": "12345678-1234-5678-1234-567812345678"\}\s*app\.dependency_overrides\[get_db\] = override_get_db\s*app\.dependency_overrides\[get_current_user_or_none\] = override_get_current_user_or_none',
    'from app.core.dependencies import get_current_user\n\n\nasync def override_get_current_user():\n    class DummyUser:\n        id = "12345678-1234-5678-1234-567812345678"\n    return DummyUser()\n\n\napp.dependency_overrides[get_db] = override_get_db\napp.dependency_overrides[get_current_user] = override_get_current_user\n',
    content
)

with open('backend/tests/integration/test_api_journal.py', 'w', encoding='utf-8') as f:
    f.write(content)
