from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.operational import AuditLog as EmailJob

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
settings = get_settings()


class EmailDeliveryError(Exception):
    """Raised when an OTP email genuinely could not be sent.

    Callers (register/forgot-password) must surface this rather than
    pretending the code was delivered - silently swallowing it would leave
    the user staring at an OTP entry page for a code that never arrives.
    """


OTP_SUBJECTS: dict[str, str] = {
    "signup": "Your NeuroQuant verification code",
    "password_reset": "Your NeuroQuant password reset code",
}


def _render_otp_body(purpose: str, code: str, expires_minutes: int) -> str:
    if purpose == "signup":
        intent = "verify your email and activate your account"
    else:
        intent = "reset your password"
    return (
        f"Use the code below to {intent}. It expires in {expires_minutes} minutes "
        f"and can only be used once.\n\n"
        f"    {code}\n\n"
        f"If you didn't request this, you can safely ignore this email - "
        f"no changes will be made to your account."
    )


async def send_otp_email(to_email: str, code: str, purpose: str) -> None:
    """Send an OTP code by email synchronously, via SendGrid.

    This intentionally bypasses the enqueue_email/Celery path above: that
    path silently no-ops whenever `tasks.email_tasks` isn't importable
    (true in this repo today - no such module exists), which is acceptable
    for best-effort notification emails but not for a code the user is
    actively waiting on to proceed through signup or password reset.
    """
    from app.core.test_state import is_test_mode

    if is_test_mode():
        return  # tests inject/know the code directly; never send real email in CI

    if not settings.SENDGRID_API_KEY:
        raise EmailDeliveryError(
            "Email delivery is not configured (SENDGRID_API_KEY missing) - cannot send OTP"
        )

    import logging

    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    subject = OTP_SUBJECTS.get(purpose, "Your NeuroQuant verification code")
    body = _render_otp_body(purpose, code, settings.OTP_EXPIRE_MINUTES)
    message = Mail(
        from_email=settings.SENDGRID_FROM_EMAIL,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body,
    )
    try:
        import asyncio

        client = SendGridAPIClient(settings.SENDGRID_API_KEY)
        await asyncio.to_thread(client.send, message)
    except Exception as exc:
        # Never include `code` in this log line.
        logging.getLogger(__name__).error(f"SendGrid OTP delivery failed for purpose={purpose}: {exc}")
        raise EmailDeliveryError("Failed to send verification email") from exc


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

    if not settings.ALERT_EMAIL_ENABLED:
        return str(job.id)

    import logging

    try:
        send_email_task.delay(str(job.id), to_email, template, payload)
    except Exception as e:
        logging.getLogger(__name__).warning(
            f"Failed to enqueue email task (Broker might be down): {e}"
        )

    return str(job.id)


def render_template(template: str, payload: dict[str, object]) -> str:
    body = TEMPLATES.get(template, "")
    return body.format(**payload)


def mark_email_job_state(job: EmailJob, status: str, error: str | None = None) -> None:
    job.status = status
    job.last_error = error
    job.attempts += 1
    job.updated_at = datetime.now(UTC)
