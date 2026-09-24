import re

with open('apps/web/src/app/[locale]/(app)/research/factor-exposure/page.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

# Remove import
text = re.sub(r'import \{ SYMBOLS as DEFAULT_SYMBOLS \} from "@/shared/constants/symbols";\n', '', text)

# Change useState
text = text.replace('useState<string>(DEFAULT_SYMBOLS[0] ?? "");', 'useState<string>("");')

# Replace select with input
select_regex = r'<select\s+value=\{symbol\}\s+onChange=\{\(event\) => setSymbol\(event\.target\.value\)\}\s+className="rounded border border-\[var\(--nq-border\)\] bg-\[var\(--nq-bg-card\)\] px-3 py-1 text-xs"\s*>\s*\{DEFAULT_SYMBOLS\.map\(\(item\) => \(\s*<option key=\{item\} value=\{item\}>\{item\}</option>\s*\)\)\}\s*</select>'

input_replacement = r'<input type="text" value={symbol} onChange={(event) => setSymbol(event.target.value.toUpperCase())} placeholder="Enter Symbol (e.g. RELIANCE.NS)" className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1 text-xs" />'

text = re.sub(select_regex, input_replacement, text, flags=re.DOTALL)

with open('apps/web/src/app/[locale]/(app)/research/factor-exposure/page.tsx', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched factor-exposure page')
