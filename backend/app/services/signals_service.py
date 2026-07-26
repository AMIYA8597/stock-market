# backend/app/services/signals_service.py
"""Signals Service – CRUD for signal definitions, execution, and LLM explanations.

This service provides:
- `list_signals(db)`: Return all stored `EnsembleSignal` records.
- `run_signal(db, symbol, payload)`: Execute the signal engine for a given ticker and payload, returning the created `EnsembleSignal`.
- `explain_signal(db, signal_id)`: Generate an explanation via the `ai_service` (uses OpenAI gpt‑4‑o‑mini) for a stored signal.

The implementation uses existing models (`EnsembleSignal`) and the `SignalEngine` from `app.services.signal_engine`.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signal import EnsembleSignal
from app.services.signal_engine import SignalEngine

logger = logging.getLogger(__name__)


async def list_signals(db: AsyncSession) -> list[EnsembleSignal]:
    """Return all EnsembleSignal entries ordered by creation time descending."""
    result = await db.execute(
        EnsembleSignal.__table__.select().order_by(EnsembleSignal.time.desc())
    )
    return result.scalars().all()


async def run_signal(
    db: AsyncSession,
    symbol: str,
    payload: dict,
) -> EnsembleSignal | None:
    """Run the signal engine for *symbol* with *payload*.

    Returns the created `EnsembleSignal` or ``None`` if the engine rejects the prediction.
    """
    return await SignalEngine.process_new_prediction(db, symbol, payload)


async def explain_signal(db: AsyncSession, signal_id: int) -> str | None:
    """Generate a natural-language explanation for a stored signal.

    Uses the PredictionEngine's explanation module when available.
    Returns None if the ML engine is not yet ready.
    """
    signal = await db.get(EnsembleSignal, signal_id)
    if not signal:
        return None
    prompt = (
        f"Explain the trading signal for ticker {signal.symbol_id} with direction "
        f"{signal.direction}, confidence {float(signal.confidence):.2%}, and raw "
        f"ensemble {float(signal.signal):.4f}."
    )
    try:
        from app.services.ai_service import predict as ai_predict

        resp = await ai_predict(db, {"prompt": prompt, "symbol": str(signal.symbol_id)})
        return resp.get("explanation") if isinstance(resp, dict) else None
    except Exception:  # noqa: BLE001
        logger.warning(f"Signal explanation generation failed for signal {signal_id}", exc_info=True)
        return None
