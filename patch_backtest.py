import re

with open('backend/app/api/v1/backtest.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r'dm_stat, dm_p = None, None, loss_b=np\.square\(benchmark_returns\)\n    \)',
    'dm_stat, dm_p = None, None',
    content
)

with open('backend/app/api/v1/backtest.py', 'w', encoding='utf-8') as f:
    f.write(content)
