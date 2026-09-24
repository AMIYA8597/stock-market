import sys, os
import yfinance as yf
sys.path.append(os.path.abspath('backend'))
from app.services.optimized_retest_strategy import calculate_retest_signals, run_optimized_backtest, summarize_trades

df = yf.download("AAPL", period="1y", interval="1h")
if hasattr(df.columns, 'droplevel'): 
    df.columns = df.columns.droplevel(1)
df.rename(columns={c: c.lower() for c in df.columns}, inplace=True)

df = calculate_retest_signals(df)
trades = run_optimized_backtest(df)
res = summarize_trades(trades)
print(f"TRADES: {res['total']} | WIN RATE: {res['win_rate']}% | PNL: {res['pnl']}%")
