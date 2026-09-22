import re

with open('backend/app/schemas/backtest.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'walk_forward: WalkForwardMetrics \| None = None', 'walk_forward: Any = None', content)
content = re.sub(r'statistical_tests: StatisticalTests \| None = None', 'statistical_tests: Any = None', content)

with open('backend/app/schemas/backtest.py', 'w', encoding='utf-8') as f:
    f.write(content)
