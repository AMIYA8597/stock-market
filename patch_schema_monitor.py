import re

with open('backend/app/schemas/monitor.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r'\s*adwin_p_value: Decimal = Field\(..., ge=0, le=1\)',
    '',
    content
)

with open('backend/app/schemas/monitor.py', 'w', encoding='utf-8') as f:
    f.write(content)
