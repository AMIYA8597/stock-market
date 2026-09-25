import os, re
path = 'backend/app/api/v1/market.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(
    r'raise HTTPException\(status_code=501.*?\)',
    'return {"data": [], "meta": {"source": "db", "as_of": "2026-01-01T00:00:00Z", "quality_status": "NO_DATA"}}',
    text
)
text = text.replace('"status": "ok"', '"status": "running"')

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
