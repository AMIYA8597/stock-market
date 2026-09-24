with open('apps/web/src/modules/signals/SignalsFeedPage.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('setSymbols(["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]);', 'setSymbols([]);')

with open('apps/web/src/modules/signals/SignalsFeedPage.tsx', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched SignalsFeedPage')
