import re

with open('apps/web/src/components/terminal/TopBar.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('import { getApiBaseUrl } from "@/lib/runtime-config";', 'import { fetchApi } from "@/lib/api-client";')

with open('apps/web/src/components/terminal/TopBar.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
