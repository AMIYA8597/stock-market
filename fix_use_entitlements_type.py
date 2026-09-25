with open('apps/web/src/hooks/useEntitlements.ts', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('await fetchApi("/payments/subscription")', 'await fetchApi<any>("/payments/subscription")')

with open('apps/web/src/hooks/useEntitlements.ts', 'w', encoding='utf-8') as f:
    f.write(text)
