import re
import os

def patch_file(path, replacements):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for p, r in replacements:
        content = re.sub(p, r, content)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

patch_file("apps/web/src/components/terminal/panes/SignalsTab.tsx", [
    (r'\?\? 0\.50', ''),
    (r'\?\? 0\.5', ''),
])

patch_file("apps/web/app/(app)/model-monitor/page.tsx", [
    (r'return 0\.85; // Default stable when data insufficient', 'return null;'),
    (r'return 0\.85', 'return null')
])

patch_file("apps/web/src/lib/intelligence-api.ts", [
    (r'function asNumber\(value: unknown, fallback = 0\): number \{', 'function asNumber(value: unknown, fallback: number | null = null): number | null {'),
    (r'return fallback;', 'return fallback;'),
    (r'const parsed = Number\(value\);', 'if (value === null || value === undefined) return fallback;\n  const parsed = Number(value);'),
    (r'return Number\.isNaN\(parsed\) \? fallback : parsed;', 'return Number.isNaN(parsed) ? fallback : parsed;'),
])
