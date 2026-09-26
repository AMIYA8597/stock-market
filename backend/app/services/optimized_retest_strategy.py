import numpy as np
import pandas as pd


def calculate_retest_signals(df: pd.DataFrame, fast_ema=10, slow_ema=30, trend_ema=50, body_pct_min=0.40) -> pd.DataFrame:
    """
    Calculates indicators for the Optimized Retest Strategy:
    - EMA 10, 30, 50
    - ADX, ATR
    - Body % > 40% filter
    - Fast EMA 3-bar slope
    """
    df = df.copy()

    # 1. EMAs
    df['ema10'] = df.ta.ema(close=df['close'], length=fast_ema)
    df['ema30'] = df.ta.ema(close=df['close'], length=slow_ema)
    df['ema50'] = df.ta.ema(close=df['close'], length=trend_ema)

    # 2. Volatility & Trend Strength
    df['atr'] = df.ta.atr(length=14)
    adx_df = df.ta.adx()
    df['adx'] = adx_df.iloc[:, 0] if adx_df is not None and not adx_df.empty else np.nan

    # 3. Candle Body Quality (Body % > 40%)
    df['body_pct'] = abs(df['close'] - df['open']) / (df['high'] - df['low']).replace(0, 1e-9)
    df['body_ok'] = df['body_pct'] >= body_pct_min

    # 4. Fast EMA Slope (3 bars)
    df['ema10_slope'] = df['ema10'] - df['ema10'].shift(3)

    # 5. Trend Alignment
    df['trend_long'] = (df['ema10'] > df['ema30']) & (df['ema30'] >= df['ema50'])
    df['trend_short'] = (df['ema10'] < df['ema30']) & (df['ema30'] <= df['ema50'])

    # Crossovers (to track new cycles)
    def crossover(s1, s2):
        return (s1 > s2) & (s1.shift(1) <= s2.shift(1))
    def crossunder(s1, s2):
        return (s1 < s2) & (s1.shift(1) >= s2.shift(1))

    df['cross_up'] = crossover(df['ema10'], df['ema30'])
    df['cross_down'] = crossunder(df['ema10'], df['ema30'])

    # 6. Retest Triggers
    # Long: Trend aligned, touches EMA10, closes green, good body, EMA curling up
    df['retest_long'] = (df['low'] <= df['ema10']) & (df['close'] > df['open']) & \
                        df['trend_long'] & df['body_ok'] & (df['ema10_slope'] > 0)

    # Short: Trend aligned, touches EMA10, closes red, good body, EMA curling down
    df['retest_short'] = (df['high'] >= df['ema10']) & (df['close'] < df['open']) & \
                         df['trend_short'] & df['body_ok'] & (df['ema10_slope'] < 0)

    return df

def run_optimized_backtest(df: pd.DataFrame):
    """
    Backtests the Optimized Retest Strategy state machine:
    - Max 2 retests per crossover cycle
    - 2nd entry ONLY if 1st is in profit
    - 1.5x ATR Stop Loss
    - Exit on EMA flip
    """
    if 'retest_long' not in df.columns:
        df = calculate_retest_signals(df)

    trades = []

    # State variables
    current_trend = 0 # 1 for long, -1 for short
    open_positions = [] # List of dicts: {'entry': px, 'sl': sl, 'type': 'LONG'/'SHORT'}
    retest_count = 0

    for idx in range(1, len(df)):
        row = df.iloc[idx]

        # 1. Check Crossovers (Trend Flips)
        if row['cross_up']:
            # Exit all short positions
            for pos in open_positions:
                if pos['type'] == 'SHORT':
                    trades.append({
                        'type': 'SHORT', 'entry': pos['entry'], 'exit': row['close'],
                        'pnl': (pos['entry'] - row['close'])/pos['entry'], 'reason': 'FLIP'
                    })
            open_positions = []
            current_trend = 1
            retest_count = 0

        elif row['cross_down']:
            # Exit all long positions
            for pos in open_positions:
                if pos['type'] == 'LONG':
                    trades.append({
                        'type': 'LONG', 'entry': pos['entry'], 'exit': row['close'],
                        'pnl': (row['close'] - pos['entry'])/pos['entry'], 'reason': 'FLIP'
                    })
            open_positions = []
            current_trend = -1
            retest_count = 0

        # 2. Check Stop Losses
        surviving_positions = []
        for pos in open_positions:
            sl_hit = False
            if pos['type'] == 'LONG' and row['low'] <= pos['sl']:
                trades.append({
                    'type': 'LONG', 'entry': pos['entry'], 'exit': pos['sl'],
                    'pnl': (pos['sl'] - pos['entry'])/pos['entry'], 'reason': 'SL'
                })
                sl_hit = True
            elif pos['type'] == 'SHORT' and row['high'] >= pos['sl']:
                trades.append({
                    'type': 'SHORT', 'entry': pos['entry'], 'exit': pos['sl'],
                    'pnl': (pos['entry'] - pos['sl'])/pos['entry'], 'reason': 'SL'
                })
                sl_hit = True

            if not sl_hit:
                surviving_positions.append(pos)
        open_positions = surviving_positions

        # 3. Check Entries (Retests)
        atr_val = row['atr'] if pd.notna(row['atr']) else (row['close']*0.01)

        if current_trend == 1 and row['retest_long']:
            can_enter = False
            if retest_count == 0:
                can_enter = True
            elif retest_count == 1:
                # Add only if first position is in profit
                if len(open_positions) > 0 and row['close'] > open_positions[0]['entry']:
                    can_enter = True

            if can_enter:
                open_positions.append({
                    'type': 'LONG',
                    'entry': row['close'],
                    'sl': row['close'] - (1.5 * atr_val)
                })
                retest_count += 1

        elif current_trend == -1 and row['retest_short']:
            can_enter = False
            if retest_count == 0:
                can_enter = True
            elif retest_count == 1:
                # Add only if first position is in profit
                if len(open_positions) > 0 and row['close'] < open_positions[0]['entry']:
                    can_enter = True

            if can_enter:
                open_positions.append({
                    'type': 'SHORT',
                    'entry': row['close'],
                    'sl': row['close'] + (1.5 * atr_val)
                })
                retest_count += 1

    return trades

def summarize_trades(trades):
    if not trades:
        return {'total': 0, 'win_rate': 0, 'pnl': 0}
    wins = [t for t in trades if t['pnl'] > 0]
    return {
        'total': len(trades),
        'wins': len(wins),
        'win_rate': round(len(wins)/len(trades)*100, 2),
        'pnl': round(sum([t['pnl'] for t in trades])*100, 2)
    }
