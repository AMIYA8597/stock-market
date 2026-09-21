import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import research.backtesting.run_walk_forward as rwf

# Keep reference to the real function
real_build_ensemble = rwf.build_ensemble_signal

# A global state to know future returns
GLOBAL_FUTURE_DIRECTION = {}

async def leaky_build_ensemble(symbol, df_slice):
    # If we don't have enough history or haven't pre-computed, just return 1.0
    if len(df_slice) < 2:
        return {"raw_ensemble": 1.0, "kelly": 0.05, "model_signals": {}}

    current_date = df_slice.index[-1]

    # Check if we have the future return precomputed
    if current_date in GLOBAL_FUTURE_DIRECTION:
        target = GLOBAL_FUTURE_DIRECTION[current_date]
        return {"raw_ensemble": float(target), "kelly": 0.05, "model_signals": {}}

    return {"raw_ensemble": 1.0, "kelly": 0.05, "model_signals": {}}

async def main():
    print("=== TESTING ENGINE-LEVEL LEAKAGE GUARD ===")

    # 1. Fetch real data first to precompute perfect targets
    symbol = "RELIANCE.NS"
    import numpy as np
    import pandas as pd
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    df = ticker.history(period="2y", interval="1d")
    df = df.reset_index().rename(columns={"Date": "time", "Datetime": "time"})
    df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)
    df.index = pd.DatetimeIndex(df["time"])

    # Precompute perfect direction for NEXT day
    # df["close"] at idx t+1 / df["close"] at idx t
    returns = df["Close"].shift(-1) / df["Close"] - 1.0
    direction = np.sign(returns).fillna(1.0)

    for dt, d in zip(df.index, direction, strict=False):
        GLOBAL_FUTURE_DIRECTION[dt] = d

    # 2. Patch the engine
    rwf.build_ensemble_signal = leaky_build_ensemble

    # 3. Run!
    try:
        await rwf.run_backtest_for_symbol(symbol, test_days=150)
        print("FAIL: The engine did not abort despite having a 100% win rate from leakage.")
    except SystemExit as e:
        print(f"SUCCESS: Engine correctly aborted due to leakage guard (exit code {e.code})!")
    except Exception as e:
        print(f"FAILED with unexpected exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
