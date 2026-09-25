import re

with open('apps/web/src/components/terminal/TopBar.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("import { getApiBaseUrl } from '@/lib/runtime-config';", "import { fetchApi } from '@/lib/api-client';")

# Find the fetch block and replace it
# const res = await fetch(`${getApiBaseUrl()}/api/v1/market/global-context`);
# if (!res.ok) throw new Error("Failed to fetch global context");
# const data = await res.json();
text = re.sub(
    r'const res = await fetch\(`\$\{getApiBaseUrl\(\)\}/api/v1/market/global-context`\);[\s\S]*?const data = await res\.json\(\);',
    r'const data = await fetchApi("/market/global-context");',
    text
)

with open('apps/web/src/components/terminal/TopBar.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
