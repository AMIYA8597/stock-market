"""AI service – routes calls to the PredictionEngine.

Train / predict wrappers used by app.api.v1.ai and app.services.signals_service.
If the underlying PredictionEngine is unavailable (models not trained yet), raises
ServiceUnavailableError so callers can surface a clean 503 instead of a fake stub.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ServiceUnavailableError(RuntimeError):
    """Raised when the ML engine is not ready (models not trained)."""


async def train_model(db: Any) -> None:  # noqa: ANN401
    """Launch an async background training job via the PredictionEngine.

    Raises ServiceUnavailableError if the engine is not installed.
    """
    try:
        from app.services.prediction_engine import PredictionEngine  # type: ignore[import]

        engine = PredictionEngine()
        await engine.train(db)
    except ImportError as exc:
        raise ServiceUnavailableError(
            "PredictionEngine module is unavailable – run the training pipeline first."
        ) from exc


async def predict(db: Any, payload: dict[str, Any]) -> dict[str, Any]:  # noqa: ANN401
    """Run inference via the PredictionEngine.

    Returns a dictionary with at least: symbol, direction, confidence, signal_score.
    Raises ServiceUnavailableError when no trained model exists for the requested symbol.
    """
    symbol: str = str(payload.get("symbol", "")).upper()

    try:
        from app.services.prediction_engine import PredictionEngine  # type: ignore[import]

        engine = PredictionEngine()
        return await engine.predict(db, symbol=symbol, payload=payload)
    except ImportError as exc:
        raise ServiceUnavailableError(
            f"PredictionEngine unavailable – models not trained for {symbol or 'unknown'}."
        ) from exc
    except FileNotFoundError as exc:
        raise ServiceUnavailableError(
            f"No trained model found for symbol '{symbol}'. Run the training pipeline first."
        ) from exc
