with open('backend/tests/integration/test_api_backtest.py', 'r') as f:
    code = f.read()

replacement = """
shared_store = {}
from app.models.user import User
u = User(id=uuid.UUID('3b79b787-f2a8-4a48-abf1-0268d6131a5b'), email='test@test.com')
shared_store[u.id] = u
"""
code = code.replace('shared_store = {}', replacement)
with open('backend/tests/integration/test_api_backtest.py', 'w') as f:
    f.write(code)
print('User added to shared_store!')
