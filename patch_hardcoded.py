import re

with open('apps/web/src/components/layout/command-palette.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

# Remove hardcoded searches
text = re.sub(r'const POPULAR_SEARCHES: SearchItem\[\] = \[.*?\];', 'const POPULAR_SEARCHES: SearchItem[] = [];', text, flags=re.DOTALL)

with open('apps/web/src/components/layout/command-palette.tsx', 'w', encoding='utf-8') as f:
    f.write(text)

with open('apps/web/src/lib/contracts-api.ts', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('universe: symbols.length > 0 ? symbols : ["RELIANCE.NS"],', 'universe: symbols,')
text = text.replace('getFactorExposure(symbol: string = "RELIANCE.NS",', 'getFactorExposure(symbol: string,')
with open('apps/web/src/lib/contracts-api.ts', 'w', encoding='utf-8') as f:
    f.write(text)

with open('apps/web/src/stores/terminalStore.ts', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace("selectedSymbol: 'RELIANCE.NS',", "selectedSymbol: '',")
with open('apps/web/src/stores/terminalStore.ts', 'w', encoding='utf-8') as f:
    f.write(text)

with open('apps/web/src/hooks/useTerminalData.ts', 'r', encoding='utf-8') as f:
    text = f.read()
text = text.replace('setSelectedSymbol(symbolsToLoad[0] ?? "RELIANCE.NS");', 'if (symbolsToLoad[0]) setSelectedSymbol(symbolsToLoad[0]);')
text = text.replace('const targetSymbol = symbolsToLoad.includes(selectedSymbol) ? selectedSymbol : (symbolsToLoad[0] ?? "RELIANCE.NS");', 'const targetSymbol = symbolsToLoad.includes(selectedSymbol) ? selectedSymbol : (symbolsToLoad[0] ?? "");')
with open('apps/web/src/hooks/useTerminalData.ts', 'w', encoding='utf-8') as f:
    f.write(text)

with open('apps/web/src/components/terminal/Watchlist.tsx', 'r', encoding='utf-8') as f:
    text = f.read()
text = re.sub(r'const getSector = \(sym: string\) => \{.*?return "Equity";\s*\};', 'const getSector = (sym: string) => { return "Equity"; };', text, flags=re.DOTALL)
with open('apps/web/src/components/terminal/Watchlist.tsx', 'w', encoding='utf-8') as f:
    f.write(text)

print("Patched hardcoded symbols")
