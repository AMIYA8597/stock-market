"""Scheduled data tasks."""

from __future__ import annotations

from celery import shared_task


@shared_task(name="tasks.data_tasks.refresh_features")
def refresh_features() -> dict[str, str]:
    """Placeholder-free deterministic task response for scheduler wiring."""
    return {"status": "ok", "task": "refresh_features"}
