import os
import hashlib
import pandas as pd
import yfinance as yf
from datetime import datetime

DATA_RAW_DIR = "data/raw"
os.makedirs(DATA_RAW_DIR, exist_ok=True)

# A small subset of NIFTY 50 for quick execution, will be expanded
TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
    "^NSEI", "^INDIAVIX"
]

def fetch_data():
    print("Fetching data from yfinance...")
    end_date = datetime.today().strftime('%Y-%m-%d')
    start_date = "2010-01-01"
    
    for ticker in TICKERS:
        print(f"Downloading {ticker}...")
        df = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if not df.empty:
            
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            df.to_csv(f"{DATA_RAW_DIR}/{ticker.replace('^', '')}.csv")
        else:
            print(f"Warning: No data for {ticker}")

def generate_manifest():
    print("Generating data manifest...")
    manifest_records = []
    for root, _, files in os.walk(DATA_RAW_DIR):
        for f in files:
            path = os.path.join(root, f)
            with open(path, "rb") as file_obj:
                file_hash = hashlib.sha256(file_obj.read()).hexdigest()
            df = pd.read_csv(path, header=[0, 1] if "yfinance" in path else 0)
            rows = len(df)
            manifest_records.append({
                "file": f,
                "rows": rows,
                "hash_sha256": file_hash
            })
    manifest = pd.DataFrame(manifest_records)
    manifest.to_csv("data_manifest.csv", index=False)
    print("Manifest saved to data_manifest.csv")

if __name__ == "__main__":
    fetch_data()
    generate_manifest()
