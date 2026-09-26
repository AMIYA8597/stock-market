import numpy as np
import pandas as pd


def calculate_ez_algo(df: pd.DataFrame,
                      ema1_len: int = 9,
                      ema2_len: int = 55,
                      custom_emas: list = [5, 8, 34, 55, 89, 144, 200]) -> pd.DataFrame:
    """
    Calculates the EZ Algo EMA Suite indicators based on the provided Pine Script.
    Expects a DataFrame with a 'close' column.
    """
    df = df.copy()

    # Calculate main EMAs
    res1 = df.ta.ema(close=df['close'], length=ema1_len)
    df['ema1'] = res1.iloc[:, 0] if isinstance(res1, pd.DataFrame) else (res1 if res1 is not None else np.nan)

    res2 = df.ta.ema(close=df['close'], length=ema2_len)
    df['ema2'] = res2.iloc[:, 0] if isinstance(res2, pd.DataFrame) else (res2 if res2 is not None else np.nan)

    # Cond1: close crossed over ema1 AND close crossed over ema2
    # In Pandas, crossover is when previous close <= previous EMA and current close > current EMA
    def crossover(series1, series2):
        return (series1 > series2) & (series1.shift(1) <= series2.shift(1))

    def crossunder(series1, series2):
        return (series1 < series2) & (series1.shift(1) >= series2.shift(1))

    df['cond1'] = crossover(df['close'], df['ema1']) & crossover(df['close'], df['ema2'])
    df['cond2'] = crossunder(df['close'], df['ema1']) & crossunder(df['close'], df['ema2'])

    # EMA 1 & EMA 2 logic
    df['ema1_crossover_ema2'] = crossover(df['ema1'], df['ema2'])
    df['ema1_crossunder_ema2'] = crossunder(df['ema1'], df['ema2'])

    # Breakout/Breakdown logic
    df['breakout'] = df['ema1_crossover_ema2']
    df['breakdown'] = df['ema1_crossunder_ema2']

    # Calculate Custom EMAs
    for i, length in enumerate(custom_emas):
        ema_num = i + 3 # Starting from EMA 3
        res = df.ta.ema(close=df['close'], length=length)
        if res is not None:
            if isinstance(res, pd.DataFrame):
                df[f'ema{ema_num}'] = res.iloc[:, 0]
            else:
                df[f'ema{ema_num}'] = res
        else:
            df[f'ema{ema_num}'] = np.nan

    return df

def generate_mtf_dashboard(symbol: str, data_by_tf: dict) -> dict:
    """
    Generates the Multi-Timeframe Dashboard status.
    data_by_tf: dictionary mapping timeframe (e.g. '1h', '4h', '1d') to its most recent row of DataFrame.
    Returns status for EMAs 9, 21, 50, 89, 100, 200.
    """
    dashboard_emas = [9, 21, 50, 89, 100, 200]
    timeframes = ['ctf', '1h', '4h', '12h', '1d', '1w']

    dashboard = {
        ema_len: {tf: None for tf in timeframes}
        for ema_len in dashboard_emas
    }

    # For each timeframe, if we have the data, calculate if close > EMA
    for tf, row in data_by_tf.items():
        if tf not in timeframes or row is None:
            continue

        close_price = row['close']
        for ema_len in dashboard_emas:
            ema_val = row.get(f'ema_{ema_len}')
            if ema_val is not None and not np.isnan(ema_val):
                dashboard[ema_len][tf] = bool(close_price > ema_val)

    return dashboard

def apply_trend_filters(df):
    """
    Applies the requested trend filters to the dataframe to avoid false signals during backtesting.
    1. ADX (Trend Strength)
    2. ATR (Volatility)
    3. Bollinger Bands (Squeeze/Width)
    4. Volume Confirmation
    5. Supertrend / PSAR
    """
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
    """
    Evaluates original EZ Algo signals (breakout/breakdown) against the selected trend filters.
    active_filters can contain: 'adx', 'atr', 'bollinger', 'volume', 'supertrend'
    """
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

def extract_trading_signals(df, active_filters=[], atr_mult=1.5, rr_ratio=5.0):
    """
    Extracts explicit trading position setups (like TradingView Long/Short Position tools)
    from the filtered signals. Returns explicit Entry, SL, and TP for the signals.
    """
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
