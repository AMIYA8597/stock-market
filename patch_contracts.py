import re
with open("apps/web/src/lib/contracts-api.ts", "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(r'\?\? 0\.5\)', ')', content)
content = re.sub(r'payload.commission_pct \?\? 0\.001', 'payload.commission_pct', content)
content = re.sub(r'payload.slippage_pct \?\? 0\.0005', 'payload.slippage_pct', content)

with open("apps/web/src/lib/contracts-api.ts", "w", encoding="utf-8") as f:
    f.write(content)
