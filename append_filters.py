import os

content = """
def apply_trend_filters(df):
    \"\"\"
    Applies the requested trend filters to the dataframe to avoid false signals during backtesting.
    1. ADX (Trend Strength)
    2. ATR (Volatility)
    3. Bollinger Bands (Squeeze/Width)
    4. Volume Confirmation
    5. Supertrend / PSAR
    \"\"\"
    # 1. ADX
    adx_df = df.ta.adx()
    if adx_df is not None and not adx_df.empty:
        df['ADX'] = adx_df.iloc[:, 0]
        
    # 2. ATR
    df['ATR'] = df.ta.atr()
    if 'ATR' in df.columns:
        df['ATR_MA'] = df['ATR'].rolling(window=14).mean()
        
    # 3. Bollinger Bands
    bbands_df = df.ta.bbands()
    if bbands_df is not None and not bbands_df.empty:
        df['BBL'] = bbands_df.iloc[:, 0]
        df['BBM'] = bbands_df.iloc[:, 1]
        df['BBU'] = bbands_df.iloc[:, 2]
        df['BB_WIDTH'] = bbands_df.iloc[:, 3]
        
    # 4. Volume Confirmation
    if 'volume' in df.columns:
        df['VOL_MA'] = df.ta.sma(close=df['volume'], length=20)
        
    # 5. Supertrend & PSAR
    supertrend_df = df.ta.supertrend()
    if supertrend_df is not None and not supertrend_df.empty:
        df['SUPERTREND'] = supertrend_df.iloc[:, 0]
        df['SUPERTREND_DIR'] = supertrend_df.iloc[:, 1]
        
    psar_df = df.ta.psar()
    if psar_df is not None and not psar_df.empty:
        # PSAR long is column 0 (usually), short is column 1
        df['PSAR_LONG'] = psar_df.iloc[:, 0]
        df['PSAR_SHORT'] = psar_df.iloc[:, 1]

    return df

def generate_filtered_signals(df, active_filters=[]):
    \"\"\"
    Evaluates original EZ Algo signals (breakout/breakdown) against the selected trend filters.
    active_filters can contain: 'adx', 'atr', 'bollinger', 'volume', 'supertrend'
    \"\"\"
    if 'breakout' not in df.columns:
        df = calculate_ez_algo(df)
        
    df = apply_trend_filters(df)
    
    # Start with base signals
    df['filtered_breakout'] = df['breakout']
    df['filtered_breakdown'] = df['breakdown']
    
    if 'adx' in active_filters and 'ADX' in df.columns:
        # ADX > 25 filter
        df['filtered_breakout'] = df['filtered_breakout'] & (df['ADX'] > 25)
        df['filtered_breakdown'] = df['filtered_breakdown'] & (df['ADX'] > 25)
        
    if 'atr' in active_filters and 'ATR' in df.columns and 'ATR_MA' in df.columns:
        # ATR > ATR_MA filter
        df['filtered_breakout'] = df['filtered_breakout'] & (df['ATR'] > df['ATR_MA'])
        df['filtered_breakdown'] = df['filtered_breakdown'] & (df['ATR'] > df['ATR_MA'])
        
    if 'bollinger' in active_filters and 'BB_WIDTH' in df.columns:
        # Bollinger Bands Expanding: BB Width > BB Width MA (e.g. 20-period moving average of width)
        df['BB_WIDTH_MA'] = df['BB_WIDTH'].rolling(window=20).mean()
        df['filtered_breakout'] = df['filtered_breakout'] & (df['BB_WIDTH'] > df['BB_WIDTH_MA'])
        df['filtered_breakdown'] = df['filtered_breakdown'] & (df['BB_WIDTH'] > df['BB_WIDTH_MA'])
        
    if 'volume' in active_filters and 'volume' in df.columns and 'VOL_MA' in df.columns:
        # Volume > Volume MA filter
        df['filtered_breakout'] = df['filtered_breakout'] & (df['volume'] > df['VOL_MA'])
        df['filtered_breakdown'] = df['filtered_breakdown'] & (df['volume'] > df['VOL_MA'])
        
    if 'supertrend' in active_filters and 'SUPERTREND_DIR' in df.columns:
        # Supertrend Dir = 1 for uptrend, -1 for downtrend
        df['filtered_breakout'] = df['filtered_breakout'] & (df['SUPERTREND_DIR'] == 1)
        df['filtered_breakdown'] = df['filtered_breakdown'] & (df['SUPERTREND_DIR'] == -1)
        
    return df
"""

with open("backend/app/services/ez_algo_service.py", "a") as f:
    f.write(content)
