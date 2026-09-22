import re

with open('backend/tests/leakage/test_leakage.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('N = warmup + 50', 'N = warmup + 250')

with open('backend/tests/leakage/test_leakage.py', 'w', encoding='utf-8') as f:
    f.write(content)
