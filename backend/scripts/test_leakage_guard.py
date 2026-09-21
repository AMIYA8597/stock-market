import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

import scripts.evaluate_models
from scripts.evaluate_models import main as evaluate_main


async def run_leakage_test():
    print("=== TASK 3: SYNTHETIC LEAKAGE TEST ===")

    # We will monkey-patch the fetch_data in evaluate_models
    # to introduce a leaky feature that gives away the target.

    async def leaky_fetch():
        import numpy as np

        print("Generating SYNTHETIC LEAKY DataFrame with 500 rows...")
        # Create 500 rows of random data
        dates = pd.date_range(start="2020-01-01", periods=500)
        df = pd.DataFrame(np.random.randn(500, 10), columns=[f"feature_{i}" for i in range(10)], index=dates)

        # Add target column (ret_1d)
        df["ret_1d"] = np.random.randn(500)

        # Inject LEAKY feature!
        df["leaked_target_future"] = (df["ret_1d"].shift(-1) > 0).astype(int)

        return df

    # Monkey patch
    scripts.evaluate_models.fetch_data = leaky_fetch

    try:
        await evaluate_main()
    except SystemExit as e:
        print(f"Evaluate System exit caught with code {e.code}")

    print("\n=== TASK 4: ENGINE-LEVEL LEAKAGE TEST (run_walk_forward) ===")

    # Original function

    async def leaky_build_ensemble(symbol, df_slice):
        # Let's peek into the FUTURE to generate an omniscient signal!
        if len(df_slice) < 2:
            return {"raw_ensemble": 0.0, "kelly": 0.05, "model_signals": {}}

        # In the engine, `df_slice` is data UP TO today.
        # But wait, if we are evaluating `run_walk_forward`, we just need to return
        # a signal that always guesses the right direction for the NEXT day's return!
        # The true return is calculated in `run_walk_forward.py` on the WHOLE `df`.
        # To simulate a leaky model, let's patch `run_backtest_for_symbol` instead,
        # or just make `build_ensemble_signal` read the future from the global scope?
        pass

    # Better approach: We can patch `yf.Ticker.history` so that df contains a leaked signal column,
    # and then patch `build_ensemble_signal` to just return that leaked signal!
    pd.DataFrame.history if hasattr(pd.DataFrame, 'history') else None

    async def omniscient_build(symbol, df_slice):
        # We will just generate random noise? No, we need it to trigger > 0.75 hit rate.
        # How do we know the next day's return?
        # Actually, in run_walk_forward.py:
        # `close_prices = df["close"].iloc[start_idx:total_len].values`
        # `prev_close_prices = df["close"].iloc[start_idx - 1 : total_len - 1].values`
        # `actual_returns = (close_prices / prev_close_prices) - 1.0`
        # `df_slice` contains up to `idx`. The NEXT day return is `df["close"].iloc[idx] / df["close"].iloc[idx-1] - 1`
        # Since `df_slice` doesn't have the next day, we can't easily peek inside `build_ensemble_signal` unless we access the global `df`.

        # However, if we just return `1.0` if `df_slice["close"].iloc[-1] > df_slice["close"].iloc[-2]` it's just momentum, might not be 75%.
        return {"raw_ensemble": 1.0, "kelly": 0.05, "model_signals": {}}

    # Let's patch `run_backtest_for_symbol`'s internal `actual_returns`!
    # No, we want to test the guard logic.
    # I'll just write a custom script to inject a leaky signal into `run_walk_forward.py`.

    # We can patch `build_ensemble_signal` to use a global df that has the whole series.
    # I'll modify `run_walk_forward.py` instead or just test it directly!
    pass

if __name__ == "__main__":
    asyncio.run(run_leakage_test())
