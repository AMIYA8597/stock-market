
path = r"d:\work\stock-market\backend\app\services\prediction_engine.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# Fix get_full_prediction signature
old_sig = "async def get_full_prediction(symbol: str, bypass_cache: bool = False) -> dict[str, Any]:"
new_sig = "async def get_full_prediction(symbol: str, bypass_cache: bool = False, artifact_path: str = None, model_version: str = None) -> dict[str, Any]:"
content = content.replace(old_sig, new_sig)

# Fix build_ensemble_signal call inside get_full_prediction
old_call = "        ensemble = await build_ensemble_signal(symbol, df)"
new_call = "        ensemble = await build_ensemble_signal(symbol, df, artifact_path, model_version)"
content = content.replace(old_call, new_call)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
