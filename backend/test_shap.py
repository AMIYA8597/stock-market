import asyncio

from app.api.v1.explain import get_shap_explanation
from app.database.connection import get_db


async def run():
    async for db in get_db():
        try:
            res=await get_shap_explanation('RELIANCE', db)
            print(res.model_dump_json(indent=2))
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            break
asyncio.run(run())
