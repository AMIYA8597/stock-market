import re

with open('apps/web/src/components/terminal/panes/BacktestingTab.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace hardcoded stats block with empty states
fallback_block = r"""setBacktestStats\(\{\s*win_rate:\s*0\.584,\s*total_trades:\s*42,\s*profit_factor:\s*1\.84,\s*max_drawdown:\s*-12\.4,\s*total_return:\s*24\.8\s*\}\);"""

text = re.sub(fallback_block, "setBacktestStats(null);", text, flags=re.DOTALL)

with open('apps/web/src/components/terminal/panes/BacktestingTab.tsx', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched BacktestingTab.tsx')
