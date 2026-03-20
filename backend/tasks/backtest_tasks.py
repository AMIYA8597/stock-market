"""Asynchronous backtest execution tasks."""

from __future__ import annotations

from celery import shared_task


@shared_task(name="tasks.backtest_tasks.run_backtest_job")
def run_backtest_job(job_id: str) -> dict[str, str]:
    """Execute backtest job by id."""
    return {"status": "ok", "job_id": job_id}
