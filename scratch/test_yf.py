import yfinance as yf
df = yf.Ticker("RELIANCE.NS").history(period="2y", interval="1d")
print("DF length:", len(df))
print(df.head())
