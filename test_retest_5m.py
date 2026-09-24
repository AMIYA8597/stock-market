import sys, os
import yfinance as yf
sys.path.append(os.path.abspath('backend'))
from app.services.optimized_retest_strategy import calculate_retest_signals, run_optimized_backtest, summarize_trades

print("Downloading AAPL 5-minute data (last 60 days)...")
# yfinance limits 5m data to 60 days
df = yf.download("AAPL", period="60d", interval="5m")
if hasattr(df.columns, 'droplevel'): 
    df.columns = df.columns.droplevel(1)
df.rename(columns={c: c.lower() for c in df.columns}, inplace=True)

# The user explicitly said:
# EMA 9/200 
# Body% > 40% (0.40)
df = calculate_retest_signals(df, fast_ema=9, slow_ema=200, trend_ema=200, body_pct_min=0.40)
trades = run_optimized_backtest(df)
res = summarize_trades(trades)
print(f"--- 5-MINUTE AAPL 9/200 EMA + 40% BODY RETEST RESULTS ---")
print(f"TRADES: {res['total']} | WIN RATE: {res['win_rate']}% | NET PNL: {res['pnl']}%")
