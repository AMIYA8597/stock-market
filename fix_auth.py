import re

with open('apps/web/src/components/auth/AuthGuard.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(r'console\.log\([^)]+\);', '', text)
text = re.sub(r'console\.warn\([^)]+\);', '', text)

with open('apps/web/src/components/auth/AuthGuard.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
