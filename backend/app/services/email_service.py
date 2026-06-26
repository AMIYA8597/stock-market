from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_job import EmailJob
# Optional email background task – use a no‑op placeholder if Celery/RQ is not installed
try:
    from tasks.email_tasks import send_email_task  # type: ignore
except ModuleNotFoundError:
    def send_email_task(*_args, **_kwargs):
        """Fallback stub – logs that email sending is disabled in this environment."""
        import logging
        logging.getLogger(__name__).warning("send_email_task called but tasks module is missing; email not sent.")


TEMPLATES: dict[str, str] = {
    "welcome": "Hello {full_name}, welcome to NeuroQuant.",
    "password_reset": "Use token {reset_token} within {expires_minutes} minutes to reset your password.",
}


async def enqueue_email(db: AsyncSession, to_email: str, template: str, payload: dict[str, object]) -> str:
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

    send_email_task.delay(str(job.id), to_email, template, payload)
    return str(job.id)


def render_template(template: str, payload: dict[str, object]) -> str:
    body = TEMPLATES.get(template, "")
    return body.format(**payload)


def mark_email_job_state(job: EmailJob, status: str, error: str | None = None) -> None:
    job.status = status
    job.last_error = error
    job.attempts += 1
    job.updated_at = datetime.now(UTC)
