with open('apps/web/src/components/terminal/Watchlist.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('await fetchApi(`/market/search?q=${encodeURIComponent(query)}`)', 'await fetchApi<any>(`/market/search?q=${encodeURIComponent(query)}`)')

with open('apps/web/src/components/terminal/Watchlist.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
