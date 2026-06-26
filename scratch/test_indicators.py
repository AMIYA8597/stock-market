import yfinance as yf
import pandas as pd
import numpy as np
import pandas_ta as ta
import sys, pathlib
project_root = pathlib.Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(project_root))
from research.feature_engineering.price_factors import PriceFactorsBuilder
from research.feature_engineering.volatility_factors import VolatilityFactorsBuilder

df = yf.Ticker("RELIANCE.NS").history(period="2y", interval="1d")
df.columns = [c.lower() for c in df.columns]
df = df.rename(columns={"stock splits": "stock_splits", "capital gains": "capital_gains"})
df = df[["open", "high", "low", "close", "volume"]].dropna()
df = df.reset_index().rename(columns={"Date": "time", "Datetime": "time"})
df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)
df.index = pd.DatetimeIndex(df["time"])
df.index.name = None

print("Before builders:", len(df))
df = PriceFactorsBuilder().transform(df)
print("After PriceFactorsBuilder:", len(df))
df = VolatilityFactorsBuilder().transform(df)
print("After VolatilityFactorsBuilder:", len(df))

df.ta.rsi(length=14, append=True)
print("After RSI:", len(df))
df.ta.macd(fast=12, slow=26, signal=9, append=True)
print("After MACD:", len(df))
df.ta.ema(length=9, append=True)
df.ta.ema(length=21, append=True)
df.ta.ema(length=50, append=True)
df.ta.ema(length=200, append=True)
print("After EMAs:", len(df))
df.ta.bbands(length=20, std=2, append=True)
df.ta.atr(length=14, append=True)
df.ta.vwap(append=True)
df.ta.adx(length=14, append=True)
df.ta.stoch(k=14, d=3, append=True)
df.ta.obv(append=True)
df.ta.supertrend(length=10, multiplier=3.0, append=True)
df.ta.cdl_pattern(name="all", append=True)
print("After all TA:", len(df))

# Check nulls per column
nulls = df.isnull().sum()
print("Nulls count:")
for col, val in nulls.items():
    if val > 0:
        print(f"  {col}: {val}")

df_cleaned = df.replace([np.inf, -np.inf], np.nan).dropna()
print("After dropna:", len(df_cleaned))
