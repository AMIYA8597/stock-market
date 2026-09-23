with open('backend/tests/integration/test_api_backtest.py', 'r') as f:
    code = f.read()

replacement = """
# Dynamically find the require_feature dependency and override it
from app.api.v1.backtest import post_backtest_run
import inspect
sig = inspect.signature(post_backtest_run)
for param in sig.parameters.values():
    if hasattr(param.default, 'dependency') and param.default.dependency:
        dep = param.default.dependency
        if dep.__name__ == '_dependency' or 'require_feature' in str(dep):
            app.dependency_overrides[dep] = lambda: {'sub': '3b79b787-f2a8-4a48-abf1-0268d6131a5b'}

def test_run_status_and_results_flow() -> None:
"""
import re
code = re.sub(r'def test_run_status_and_results_flow\(\) -> None:', replacement, code)
with open('backend/tests/integration/test_api_backtest.py', 'w') as f:
    f.write(code)
print('Dynamic override added!')
