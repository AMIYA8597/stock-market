import re

with open("app/tasks/regime_tasks.py", "r") as f:
    code = f.read()

# Replace imports
code = re.sub(r'from app\.services\.regime_analyzer import GARCHVolatilityModel, HMMRegimeModel\n?', 'from research.models.hmm_garch.inference import InferenceEngine\n', code)

pattern = re.compile(r'            # Run GARCH model.*?            canonical_probs\[2\] = prob', re.DOTALL)

replacement = """            # Use the canonical InferenceEngine which wraps StudentTHMM and arch GARCH
            # We rebuild df correctly from ohlcv_records
            df_full = pd.DataFrame([
                {
                    "time": r.time,
                    "open": float(r.open) if hasattr(r, 'open') else float(r.close),
                    "high": float(r.high) if hasattr(r, 'high') else float(r.close),
                    "low": float(r.low) if hasattr(r, 'low') else float(r.close),
                    "close": float(r.close),
                    "volume": float(r.volume) if hasattr(r, 'volume') else 0.0
                }
                for r in reversed(ohlcv_records)
            ])
            df_full.set_index("time", inplace=True)
            
            ohlcv_data = df_full[["open", "high", "low", "close", "volume"]].astype(float).values
            
            engine = InferenceEngine()
            res = engine.predict(ohlcv_data, train=True)
            
            canonical_state_idx = res.current_state
            
            canonical_probs = [0.0, 0.0, 0.0, 0.0]
            for i in range(len(res.state_probs)):
                if i < 4:
                    canonical_probs[i] = float(res.state_probs[i])
                    
            cond_vol_1d = float(res.conditional_vol)
            cond_vol_5d = float(res.vol_forecast_5d)
            cond_vol_21d = float(res.vol_forecast_21d)"""

if pattern.search(code):
    print("Found regime logic, replacing...")
    new_code = pattern.sub(replacement, code)
    with open("app/tasks/regime_tasks.py", "w") as f:
        f.write(new_code)
else:
    print("Regime logic not found!")
