import re

with open('scripts/honesty_guard.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_patterns = '''    "FAKE_T": re.compile(r"2\.13"),
    "FAKE_P": re.compile(r"0\.045"),
    "FAKE_BONFERRONI": re.compile(r"Bonferroni"),
    "BANNED_OPENAI": re.compile(r"api\.openai\.com"),
    "FAKE_HOLTWINTERS": re.compile(r"Holt-Winters"),
    "FAKE_PVALUE": re.compile(r"\.pvalue"),
    "FAKE_PROBA": re.compile(r"predict_proba\(X\)\[0\]"),
    "FAKE_NOISE": re.compile(r"np\.random\.normal\("),'''

content = re.sub(
    r'"SECRET_POSTGRES":',
    new_patterns + '\n    "SECRET_POSTGRES":',
    content
)

with open('scripts/honesty_guard.py', 'w', encoding='utf-8') as f:
    f.write(content)
