import re

with open('backend/app/api/v1/backtest.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix walk_forward dict
content = re.sub(
    r'"walk_forward":\s*\{.*?"p_value": 0\.045,\s*\},',
    '"walk_forward": {"method": None, "reason": "not_computed"},',
    content,
    flags=re.DOTALL
)

# Fix statistical_tests dict
content = re.sub(
    r'"statistical_tests":\s*\{.*?"multiple_testing_correction": "Bonferroni",\s*\},',
    '"statistical_tests": {"method": None, "reason": "not_computed"},',
    content,
    flags=re.DOTALL
)

# Fix metrics deflated_sharpe
content = re.sub(
    r'"deflated_sharpe": safe_round\(deflated_sharpe, 4\),',
    '"deflated_sharpe": {"method": None, "reason": "not_computed"},',
    content
)

with open('backend/app/api/v1/backtest.py', 'w', encoding='utf-8') as f:
    f.write(content)
