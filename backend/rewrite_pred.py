import re
import sys

with open('d:/work/stock-market/backend/app/services/prediction_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix agreement default in build_ensemble_signal_sync
# Find:
#     if len(active_signals) > 0:
#         pos = sum(1 for s in active_signals if s > 0.1)
#         neg = sum(1 for s in active_signals if s < -0.1)
#         total_votes = pos + neg
#         agreement = max(pos, neg) / total_votes if total_votes > 0 else 0.5
#     else:
#         agreement = 0.5
# Replace with:
#     if len(active_signals) > 0:
#         pos = sum(1 for s in active_signals if s > 0.1)
#         neg = sum(1 for s in active_signals if s < -0.1)
#         total_votes = pos + neg
#         agreement = max(pos, neg) / total_votes if total_votes > 0 else 0.0
#     else:
#         raise ValueError("No active signals to form an ensemble.")

old_agg = """    if len(active_signals) > 0:
        pos = sum(1 for s in active_signals if s > 0.1)
        neg = sum(1 for s in active_signals if s < -0.1)
        total_votes = pos + neg
        agreement = max(pos, neg) / total_votes if total_votes > 0 else 0.5
    else:
        agreement = 0.5"""

new_agg = """    if len(active_signals) > 0:
        pos = sum(1 for s in active_signals if s > 0.1)
        neg = sum(1 for s in active_signals if s < -0.1)
        total_votes = pos + neg
        agreement = max(pos, neg) / total_votes if total_votes > 0 else 0.0
    else:
        raise ValueError("No active signals to form an ensemble. Model generation failed.")"""

text = text.replace(old_agg, new_agg)

# Also fix get_full_prediction to write to DB
# Find:
#     await _cache_store(symbol, result)
#     return result
# Add DB write before caching
db_write = """
    try:
        from app.database.connection import async_session_factory
        from sqlalchemy import select
        from app.models.market import Instrument
        from app.models.research import Prediction, ModelExplanation, ModelRegistry
        
        async with async_session_factory() as session:
            inst = (await session.execute(select(Instrument).where(Instrument.canonical_symbol == symbol))).scalars().first()
            if inst:
                # Find active model registry for XGBoost or whatever is used
                # We'll just pick the active XGBoost model for now
                active_model = (await session.execute(
                    select(ModelRegistry)
                    .where((ModelRegistry.status == "active") & (ModelRegistry.model_family == "XGBoost"))
                    .order_by(ModelRegistry.created_at.desc())
                )).scalars().first()
                
                if active_model:
                    import json
                    pred = Prediction(
                        model_id=active_model.id,
                        instrument_id=inst.id,
                        prediction_timestamp=datetime.now(UTC),
                        predicted_value=json.dumps(result)
                    )
                    session.add(pred)
                    await session.flush()
                    
                    expl = ModelExplanation(
                        prediction_id=pred.id,
                        explanation_data={"reasoning": reasoning_msg, "features": ensemble.get("top_features", [])}
                    )
                    session.add(expl)
                    await session.commit()
    except Exception as e:
        logger.error(f"Failed to persist prediction to database: {e}")

    await _cache_store(symbol, result)
    return result
"""

text = text.replace("    await _cache_store(symbol, result)\n    return result", db_write)


with open('d:/work/stock-market/backend/app/services/prediction_engine.py', 'w', encoding='utf-8') as f:
    f.write(text)
