with open("backend/tests/integration/test_api_backtest.py", "r") as f:
    code = f.read()

replacement = """
from app.core.security import get_current_context, RequestContext
async def override_get_current_context():
    return RequestContext(
        user_id=uuid.UUID("3b79b787-f2a8-4a48-abf1-0268d6131a5b"),
        organization_id=uuid.UUID("3b79b787-f2a8-4a48-abf1-0268d6131a5b"),
        organization_role="OWNER"
    )
app.dependency_overrides[get_current_context] = override_get_current_context

async def override_get_current_user():
"""

code = code.replace("async def override_get_current_user():", replacement)

with open("backend/tests/integration/test_api_backtest.py", "w") as f:
    f.write(code)

print("Fixed!")
