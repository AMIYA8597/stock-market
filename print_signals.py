import sys, os
import yfinance as yf
sys.path.append(os.path.abspath('backend'))
from app.services.ez_algo_service import extract_trading_signals, calculate_ez_algo, apply_trend_filters

df = yf.download("AAPL", period="1mo", interval="1h")
if hasattr(df.columns, 'droplevel'): 
    df.columns = df.columns.droplevel(1)
df.rename(columns={c: c.lower() for c in df.columns}, inplace=True)

df = calculate_ez_algo(df)
df = apply_trend_filters(df)
signals = extract_trading_signals(df, active_filters=['adx', 'supertrend'], rr_ratio=5.0)

for s in signals[-5:]:
    print(f"{s['timestamp']} | {s['action']} @ {s['entry']} | SL: {s['stop_loss']} | TP: {s['take_profit']} | RR: {s['target_type']}")
