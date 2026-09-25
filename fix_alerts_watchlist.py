import re

with open('apps/web/src/components/terminal/Watchlist.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(
    r'const apiUrl = process\.env\.NEXT_PUBLIC_API_URL[\s\S]*?const data = await res\.json\(\);',
    r'const data = await fetchApi(`/market/search?q=${encodeURIComponent(query)}`);',
    text
)

with open('apps/web/src/components/terminal/Watchlist.tsx', 'w', encoding='utf-8') as f:
    f.write(text)

with open('apps/web/src/components/terminal/panes/AlertsManager.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace create fetch
text = re.sub(
    r'const apiUrl = process\.env\.NEXT_PUBLIC_API_URL[\s\S]*?if \(!res\.ok\) throw new Error\("Failed to create alert"\);',
    r'await fetchApi("/alerts", { method: "POST", body: JSON.stringify(payload) });',
    text
)

# Replace fetch for loading
text = re.sub(
    r'const apiUrl = process\.env\.NEXT_PUBLIC_API_URL[\s\S]*?if \(!res\.ok\) throw new Error\("Failed to load alerts"\);[\s\S]*?const data = await res\.json\(\);',
    r'const data = await fetchApi<any[]>("/alerts");',
    text
)

# Replace delete
text = re.sub(
    r'const apiUrl = process\.env\.NEXT_PUBLIC_API_URL[\s\S]*?if \(!res\.ok\) throw new Error\("Failed to delete alert"\);',
    r'await fetchApi(`/alerts/${id}`, { method: "DELETE" });',
    text
)

with open('apps/web/src/components/terminal/panes/AlertsManager.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
