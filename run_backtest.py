import sys
import os
import pandas as pd
import yfinance as yf
import numpy as np

# Add backend to path so we can import ez_algo_service
sys.path.append(os.path.abspath('backend'))
from app.services.ez_algo_service import calculate_ez_algo, apply_trend_filters, generate_filtered_signals

def run_backtest(df, active_filters, rr_ratio):
    # Get filtered signals
    df_signals = generate_filtered_signals(df.copy(), active_filters)
    
    in_trade = False
    trade_type = None
    entry_price = 0
    sl = 0
    tp = 0
    
    trades = []
    
    # Simple ATR multiplier for Stop Loss
    atr_mult = 1.5
    
    for i in range(1, len(df_signals)):
        row = df_signals.iloc[i]
        
        if in_trade:
            # Check for exit
            if trade_type == 'LONG':
                if row['low'] <= sl:
                    trades.append({'type': 'LONG', 'entry': entry_price, 'exit': sl, 'pnl': (sl - entry_price)/entry_price, 'result': 'LOSS'})
                    in_trade = False
                elif row['high'] >= tp:
                    trades.append({'type': 'LONG', 'entry': entry_price, 'exit': tp, 'pnl': (tp - entry_price)/entry_price, 'result': 'WIN'})
                    in_trade = False
            elif trade_type == 'SHORT':
                if row['high'] >= sl:
                    trades.append({'type': 'SHORT', 'entry': entry_price, 'exit': sl, 'pnl': (entry_price - sl)/entry_price, 'result': 'LOSS'})
                    in_trade = False
                elif row['low'] <= tp:
                    trades.append({'type': 'SHORT', 'entry': entry_price, 'exit': tp, 'pnl': (entry_price - tp)/entry_price, 'result': 'WIN'})
                    in_trade = False
        
        if not in_trade:
            # Check for entry
            if row.get('filtered_breakout', False):
                in_trade = True
                trade_type = 'LONG'
                entry_price = row['close']
                atr = row['ATR'] if pd.notna(row.get('ATR', np.nan)) else (entry_price * 0.01)
                sl = entry_price - (atr * atr_mult)
                risk = entry_price - sl
                tp = entry_price + (risk * rr_ratio)
            elif row.get('filtered_breakdown', False):
                in_trade = True
                trade_type = 'SHORT'
                entry_price = row['close']
                atr = row['ATR'] if pd.notna(row.get('ATR', np.nan)) else (entry_price * 0.01)
                sl = entry_price + (atr * atr_mult)
                risk = sl - entry_price
                tp = entry_price - (risk * rr_ratio)
                
    wins = [t for t in trades if t['result'] == 'WIN']
    losses = [t for t in trades if t['result'] == 'LOSS']
    win_rate = len(wins) / len(trades) if trades else 0
    total_pnl = sum([t['pnl'] for t in trades])
    
    return {
        'filters': active_filters if active_filters else ['None'],
        'rr': f"1:{rr_ratio}",
        'total_trades': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': round(win_rate * 100, 2),
        'total_pnl_pct': round(total_pnl * 100, 2)
    }

if __name__ == "__main__":
    print("Downloading historical data for AAPL...")
    df = yf.download("AAPL", period="1y", interval="1h")
    # Clean multiindex columns if any
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
        
    df.rename(columns={c: c.lower() for c in df.columns}, inplace=True)
    
    # Calculate base signals to ensure columns exist
    df = calculate_ez_algo(df)
    df = apply_trend_filters(df)
    
    filters_to_test = [
        [],
        ['adx'],
        ['atr'],
        ['bollinger'],
        ['volume'],
        ['supertrend']
    ]
    
    for rr in [2, 3]:
        print(f"\n--- Testing 1:{rr} Risk:Reward ---")
        for f in filters_to_test:
            res = run_backtest(df, f, rr)
            print(f"Filters: {str(res['filters']):<15} | Trades: {res['total_trades']:<4} | Win Rate: {res['win_rate']:>5}% | Net PnL: {res['total_pnl_pct']:>6}%")
