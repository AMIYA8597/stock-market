import asyncio
import json

from app.services.prediction_engine import get_full_prediction


async def run():
    try:
        # Assuming LSTM is active
        res = await get_full_prediction("RELIANCE", bypass_cache=True, artifact_path="d:\\work\\stock-market\\backend\\data\\models\\lstm_attention_RELIANCE.pkl", model_version="1.0.0")
        print(json.dumps(res, indent=2))
    except Exception:
        import traceback
        traceback.print_exc()

asyncio.run(run())
