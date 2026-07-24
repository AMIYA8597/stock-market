
path = r"d:\work\stock-market\backend\app\services\prediction_engine.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

# Fix build_ensemble_signal signature
old_sig_async = "async def build_ensemble_signal(symbol: str, df: pd.DataFrame) -> dict[str, Any]:\n    return await asyncio.to_thread(build_ensemble_signal_sync, symbol, df)"
new_sig_async = "async def build_ensemble_signal(symbol: str, df: pd.DataFrame, artifact_path: str = None, model_version: str = None) -> dict[str, Any]:\n    return await asyncio.to_thread(build_ensemble_signal_sync, symbol, df, artifact_path, model_version)"
content = content.replace(old_sig_async, new_sig_async)

old_sig_sync = "def build_ensemble_signal_sync(symbol: str, df: pd.DataFrame) -> dict[str, Any]:"
new_sig_sync = "def build_ensemble_signal_sync(symbol: str, df: pd.DataFrame, artifact_path: str = None, model_version: str = None) -> dict[str, Any]:"
content = content.replace(old_sig_sync, new_sig_sync)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
