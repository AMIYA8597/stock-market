import re

with open('apps/web/src/hooks/useTerminalData.ts', 'r', encoding='utf-8') as f:
    text = f.read()

# Remove FALLBACK_SYMBOLS
text = re.sub(r'const FALLBACK_SYMBOLS = \[.*?\];', '', text, flags=re.DOTALL)

# Replace useState with empty
text = text.replace('useState<string>(FALLBACK_SYMBOLS[0] ?? "RELIANCE.NS")', 'useState<string>("")')

# Replace symbolsRef
text = text.replace('symbolsRef.current = FALLBACK_SYMBOLS;', 'symbolsRef.current = [];')

# Replace setSymbols
text = text.replace('setSymbols(FALLBACK_SYMBOLS);', 'setSymbols([]);')

# Replace setWlLists
text = text.replace('setWlLists([FALLBACK_SYMBOLS, [], [], []]);', 'setWlLists([[], [], [], []]);')

# Replace return
text = text.replace('return FALLBACK_SYMBOLS;', 'return [];')

with open('apps/web/src/hooks/useTerminalData.ts', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched useTerminalData.ts')
