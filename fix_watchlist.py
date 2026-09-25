import re

with open('apps/web/src/components/terminal/Watchlist.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("import { getApiBaseUrl } from '@/lib/runtime-config';", "")

text = re.sub(
    r'const apiUrl = getApiBaseUrl\(\);\s*const res = await fetch\(`\$\{apiUrl\}/api/v1/market/search\?q=\$\{encodeURIComponent\(query\)\}`\);[\s\S]*?const data = await res\.json\(\);',
    r'const data = await fetchApi(`/market/search?q=${encodeURIComponent(query)}`);',
    text
)
# Make sure fetchApi is imported
if 'fetchApi' not in text:
    text = text.replace('import { Search', 'import { fetchApi } from "@/lib/api-client";\nimport { Search')

with open('apps/web/src/components/terminal/Watchlist.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
