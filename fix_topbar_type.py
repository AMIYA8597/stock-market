with open('apps/web/src/components/terminal/TopBar.tsx', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('await fetchApi("/market/global-context")', 'await fetchApi<any>("/market/global-context")')
with open('apps/web/src/components/terminal/TopBar.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
