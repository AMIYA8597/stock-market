"""Model retraining tasks."""

from __future__ import annotations

from celery import shared_task


@shared_task(name="tasks.training_tasks.retrain_model")
def retrain_model(model_name: str) -> dict[str, str]:
    """Retrain one model family."""
    return {"status": "ok", "model": model_name}
