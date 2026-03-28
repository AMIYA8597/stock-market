from __future__ import annotations

from celery import shared_task


@shared_task(
    name="tasks.email_tasks.send_email",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def send_email_task(self, job_id: str, to_email: str, template: str, payload: dict[str, object]) -> dict[str, str]:
    # Placeholder transport integration point (SendGrid/SES).
    # This task intentionally retries transient failures via Celery.
    if "@" not in to_email:
        raise ValueError("Invalid recipient")

    return {
        "job_id": job_id,
        "status": "sent",
        "recipient": to_email,
        "template": template,
    }
