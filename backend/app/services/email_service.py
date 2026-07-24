from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_job import EmailJob

# Optional email background task – use a local logger if Celery/RQ is not installed
try:
    from tasks.email_tasks import send_email_task  # type: ignore
except ModuleNotFoundError:

    class OfflineLogTask:
        def delay(self, job_id, to_email, template, payload):
            import logging

            logging.getLogger(__name__).info(
                f"Offline mode: simulated sending email to {to_email} with template {template}"
            )

    send_email_task = OfflineLogTask()


TEMPLATES: dict[str, str] = {
    "welcome": "Hello {full_name}, welcome to NeuroQuant.",
    "password_reset": "Use token {reset_token} within {expires_minutes} minutes to reset your password.",
}


async def enqueue_email(
    db: AsyncSession, to_email: str, template: str, payload: dict[str, object]
) -> str:
    if template not in TEMPLATES:
        raise ValueError(f"Unsupported email template: {template}")

    job = EmailJob(
        to_email=to_email,
        template=template,
        payload_json=json.dumps(payload),
        status="queued",
    )
    db.add(job)
    await db.flush()

    import logging
    try:
        send_email_task.delay(str(job.id), to_email, template, payload)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to enqueue email task (Broker might be down): {e}")

    return str(job.id)


def render_template(template: str, payload: dict[str, object]) -> str:
    body = TEMPLATES.get(template, "")
    return body.format(**payload)


def mark_email_job_state(job: EmailJob, status: str, error: str | None = None) -> None:
    job.status = status
    job.last_error = error
    job.attempts += 1
    job.updated_at = datetime.now(UTC)
