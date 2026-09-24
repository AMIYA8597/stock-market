import os

content = """
def extract_trading_signals(df, active_filters=[], atr_mult=1.5, rr_ratio=5.0):
    \"\"\"
    Extracts explicit trading position setups (like TradingView Long/Short Position tools)
    from the filtered signals. Returns explicit Entry, SL, and TP for the signals.
    \"\"\"
    if 'filtered_breakout' not in df.columns:
        # Assuming generate_filtered_signals is defined in the same module
        df = generate_filtered_signals(df, active_filters)
        
    signals = []
    
    # We only care about rows where a signal triggered
    signal_rows = df[(df['filtered_breakout'] == True) | (df['filtered_breakdown'] == True)]
    
    for idx, row in signal_rows.iterrows():
        entry_price = row['close']
        atr = row['ATR'] if pd.notna(row.get('ATR', np.nan)) else (entry_price * 0.01)
        
        if row.get('filtered_breakout', False):
            sl = entry_price - (atr * atr_mult)
            risk = entry_price - sl
            tp = entry_price + (risk * rr_ratio)
            
            signals.append({
                'timestamp': str(idx),
                'action': 'LONG',
                'entry': round(entry_price, 4),
                'stop_loss': round(sl, 4),
                'take_profit': round(tp, 4),
                'risk_reward': rr_ratio,
                'risk_per_share': round(risk, 4),
                'target_type': '1:5 Fixed Target' if rr_ratio == 5.0 else f'1:{rr_ratio} Fixed Target'
            })
            
        elif row.get('filtered_breakdown', False):
            sl = entry_price + (atr * atr_mult)
            risk = sl - entry_price
            tp = entry_price - (risk * rr_ratio)
            
            signals.append({
                'timestamp': str(idx),
                'action': 'SHORT',
                'entry': round(entry_price, 4),
                'stop_loss': round(sl, 4),
                'take_profit': round(tp, 4),
                'risk_reward': rr_ratio,
                'risk_per_share': round(risk, 4),
                'target_type': '1:5 Fixed Target' if rr_ratio == 5.0 else f'1:{rr_ratio} Fixed Target'
            })
            
    return signals
"""

with open("backend/app/services/ez_algo_service.py", "a") as f:
    f.write(content)
