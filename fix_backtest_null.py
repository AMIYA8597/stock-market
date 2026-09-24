import re

with open('apps/web/src/components/terminal/panes/BacktestingTab.tsx', 'r', encoding='utf-8') as f:
    orig = f.read()

# Fix initial state definition
orig = orig.replace(
    'const [backtestStats, setBacktestStats] = useState<BacktestStats>({\n    win_rate: 0,\n    total_trades: 0,\n    profit_factor: 0,\n    max_drawdown: 0,\n    total_return: 0\n  });', 
    'const [backtestStats, setBacktestStats] = useState<BacktestStats | null>(null);'
)

# Replace access to backtestStats in JSX with optional chaining or conditional rendering
orig = re.sub(
    r'<div className="grid grid-cols-5 gap-2 mb-4">.*?</div>\s*</div>',
    r'''{backtestStats ? (
          <div className="grid grid-cols-5 gap-2 mb-4">
            <div className="rounded glass-panel glow-hover p-1.5 border border-[var(--nq-border)]" style={{ animationDelay: '50ms' }}>
              <p className="text-[8px] text-[var(--nq-text-muted)] uppercase">Win Rate</p>
              <p className="text-xs font-bold text-[var(--nq-accent-green)]">
                {safeFormat(backtestStats.win_rate * 100, 1)}%
              </p>
            </div>
            <div className="rounded glass-panel glow-hover p-1.5 border border-[var(--nq-border)]" style={{ animationDelay: '100ms' }}>
              <p className="text-[8px] text-[var(--nq-text-muted)] uppercase">Trades</p>
              <p className="text-xs font-bold text-[var(--nq-text-primary)]">
                {backtestStats.total_trades}
              </p>
            </div>
            <div className="rounded glass-panel glow-hover p-1.5 border border-[var(--nq-border)]" style={{ animationDelay: '150ms' }}>
              <p className="text-[8px] text-[var(--nq-text-muted)] uppercase">Profit Factor</p>
              <p className="text-xs font-bold text-[var(--nq-accent-green)]">
                {safeFormat(backtestStats.profit_factor, 2)}
              </p>
            </div>
            <div className="rounded glass-panel glow-hover p-1.5 border border-[var(--nq-border)]" style={{ animationDelay: '200ms' }}>
              <p className="text-[8px] text-[var(--nq-text-muted)] uppercase">Max DD</p>
              <p className="text-xs font-bold text-[var(--nq-accent-red)]">
                {safeFormat(backtestStats.max_drawdown, 1)}%
              </p>
            </div>
            <div className="rounded glass-panel glow-hover p-1.5 border border-[var(--nq-border)]" style={{ animationDelay: '250ms' }}>
              <p className="text-[8px] text-[var(--nq-text-muted)] uppercase">Return</p>
              <p className="text-xs font-bold text-[var(--nq-accent-green)]">
                +{safeFormat(backtestStats.total_return, 1)}%
              </p>
            </div>
          </div>
        ) : (
          <div className="text-xs text-[var(--nq-text-muted)] mb-4">Backtest result is not available yet.</div>
        )}
      </div>''',
    orig,
    flags=re.DOTALL
)

with open('apps/web/src/components/terminal/panes/BacktestingTab.tsx', 'w', encoding='utf-8') as f:
    f.write(orig)

print("Fixed backtestStats nulls")
