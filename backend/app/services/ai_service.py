"""AI service placeholder for training and prediction.

Provides async functions `train_model(db, ...)` and `predict(db, payload)`.

Currently implements simple mock behavior to satisfy imports and enable further development.
"""

from typing import Any, Dict


async def train_model(db: Any) -> None:
    """Placeholder training start.

    In production this would launch an async training job.
    """
    # No actual training; just a stub.
    return


async def predict(db: Any, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Return a dummy prediction response.

    Args:
        db: Database session (unused in stub).
        payload: Input data for prediction.

    Returns:
        Dict with dummy fields: prediction, confidence, explanation.
    """
    # Simple mock: echo input and provide dummy values.
    return {
        "prediction": "HOLD",
        "confidence": 0.5,
        "explanation": "Model placeholder; no real inference performed.",
        "input": payload,
    }
