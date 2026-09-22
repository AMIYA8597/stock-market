import re
with open("apps/web/src/lib/intelligence-api.ts", "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(r'function asNumber\(value: unknown, fallback: number \| null = null\): number \| null \{\n  const numeric = typeof value === "number" \? value : typeof value === "string" \? Number\(value\) : NaN;\n  return Number.isFinite\(numeric\) \? numeric : fallback;\n\}', 'function asNumber(value: unknown): number | null {\n  if (value === null || value === undefined) return null;\n  const numeric = typeof value === "number" ? value : typeof value === "string" ? Number(value) : NaN;\n  return Number.isFinite(numeric) ? numeric : null;\n}', content)

with open("apps/web/src/lib/intelligence-api.ts", "w", encoding="utf-8") as f:
    f.write(content)
