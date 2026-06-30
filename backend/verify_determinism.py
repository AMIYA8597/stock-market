import asyncio
import numpy as np
from app.services.prediction_engine import get_full_prediction

async def main():
    print("Testing full prediction engine determinism (Dict outputs)...")
    
    # 1. Call get_full_prediction twice
    res1 = await get_full_prediction("RELIANCE.NS")
    ens1 = res1["ensemble"]
    print("\nRun 1 ensemble output:")
    print(f"  Symbol: {res1.get('symbol')}")
    print(f"  Price: {res1.get('current_price')}")
    print(f"  Raw Ensemble Signal: {ens1.get('raw_ensemble')}")
    print(f"  Confidence: {ens1.get('confidence')}")
    print(f"  Kelly Fraction: {ens1.get('kelly')}")
    print(f"  Weights: {ens1.get('model_weights')}")
    
    # Wait 2 seconds
    await asyncio.sleep(2)
    
    res2 = await get_full_prediction("RELIANCE.NS")
    ens2 = res2["ensemble"]
    print("\nRun 2 ensemble output:")
    print(f"  Symbol: {res2.get('symbol')}")
    print(f"  Price: {res2.get('current_price')}")
    print(f"  Raw Ensemble Signal: {ens2.get('raw_ensemble')}")
    print(f"  Confidence: {ens2.get('confidence')}")
    print(f"  Kelly Fraction: {ens2.get('kelly')}")
    print(f"  Weights: {ens2.get('model_weights')}")
    
    # 2. Assert exact match
    try:
        assert np.isclose(float(res1['current_price']), float(res2['current_price']), atol=1e-7)
        assert np.isclose(float(ens1['raw_ensemble']), float(ens2['raw_ensemble']), atol=1e-7)
        assert np.isclose(float(ens1['confidence']), float(ens2['confidence']), atol=1e-7)
        assert np.isclose(float(ens1['kelly']), float(ens2['kelly']), atol=1e-7)
        for model in ens1['model_weights']:
            assert np.isclose(float(ens1['model_weights'][model]), float(ens2['model_weights'][model]), atol=1e-7)
        print("\nSUCCESS: Prediction engine is 100% deterministic!")
    except AssertionError as e:
        print("\nERROR: Prediction outputs are NOT identical! Determinism check failed.")
        raise e

if __name__ == "__main__":
    asyncio.run(main())
