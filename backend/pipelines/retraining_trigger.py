"""Retraining trigger bridge from drift detection signals."""

from __future__ import annotations

from app.core.celery_app import celery_app


def dispatch_retraining_if_drift(model_name: str, drift_detected: bool) -> str | None:
    """Dispatch async retraining task when drift is detected."""
    if not drift_detected:
        return None
    task = celery_app.send_task("tasks.training_tasks.retrain_model", args=[model_name])
    return str(task.id)
