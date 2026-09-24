import os

with open('backend/app/services/optimized_retest_strategy.py', 'r') as f:
    text = f.read()

# Make it parameterized
text = text.replace(
    "def calculate_retest_signals(df: pd.DataFrame) -> pd.DataFrame:",
    "def calculate_retest_signals(df: pd.DataFrame, fast_ema=10, slow_ema=30, trend_ema=50, body_pct_min=0.40) -> pd.DataFrame:"
)

text = text.replace("df['ema10'] = df.ta.ema(close=df['close'], length=10)", "df['ema10'] = df.ta.ema(close=df['close'], length=fast_ema)")
text = text.replace("df['ema30'] = df.ta.ema(close=df['close'], length=30)", "df['ema30'] = df.ta.ema(close=df['close'], length=slow_ema)")
text = text.replace("df['ema50'] = df.ta.ema(close=df['close'], length=50)", "df['ema50'] = df.ta.ema(close=df['close'], length=trend_ema)")
text = text.replace("df['body_ok'] = df['body_pct'] >= 0.40", "df['body_ok'] = df['body_pct'] >= body_pct_min")

with open('backend/app/services/optimized_retest_strategy.py', 'w') as f:
    f.write(text)
