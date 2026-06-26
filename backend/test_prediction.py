import sys, pathlib, asyncio, json
# Ensure project root is on PYTHONPATH
project_root = pathlib.Path(__file__).resolve().parent
sys.path.append(str(project_root))
from app.services.prediction_engine import get_full_prediction

async def main():
    symbols = ["RELIANCE.NS", "TCS.NS"]
    for sym in symbols:
        res = await get_full_prediction(sym)
        out = {
            "symbol": sym,
            "price": res.get("current_price"),
            "confidence": res.get("ensemble", {}).get("confidence"),
            "raw_ensemble": res.get("ensemble", {}).get("raw_ensemble"),
            "xgboost_train": res.get("ensemble", {}).get("xgboost", {}).get("train_samples"),
            "rsi": res.get("ensemble", {}).get("technical", {}).get("rsi"),
        }
        print(json.dumps(out, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
