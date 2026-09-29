"""Email OTP generation/verification and password-strength policy.

OTP codes are generated with `secrets` (CSPRNG), never `random`. Only a
bcrypt hash of the code is ever persisted or compared - the plaintext code
exists only in memory for the few seconds it takes to render the email, and
is never logged.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.auth_security import EmailOTP

settings = get_settings()

# Hashing goes straight to the `bcrypt` package rather than through
# passlib's CryptContext. passlib 1.7.4 (the latest release) runs an
# internal self-test on first use that calls bcrypt with a fixed internal
# string, and bcrypt>=4.1's stricter 72-byte validation makes that self-test
# raise - passlib has had no release since to account for it. Since this
# app already depends on `bcrypt` directly, using it without passlib's
# abstraction avoids the incompatibility entirely rather than pinning to an
# older, unmaintained bcrypt.
_BCRYPT_MAX_BYTES = 72


def _truncate_to_bcrypt_limit(secret: str) -> bytes:
    return secret.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_truncate_to_bcrypt_limit(password), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_truncate_to_bcrypt_limit(password), hashed.encode("ascii"))
    except ValueError:
        return False

# Small, well-known weak/breached password blocklist. This is a floor, not a
# substitute for a full breached-password corpus (e.g. HaveIBeenPwned's k-
# anonymity API) - wiring that up would need outbound network access from
# every register/reset call, which isn't available in this environment, so
# it's flagged as a known limitation rather than silently skipped.
COMMON_PASSWORDS = {
    "password", "password1", "password123", "12345678", "123456789",
    "qwerty123", "letmein", "welcome1", "admin123", "iloveyou",
    "sunshine1", "princess1", "football1", "monkey123", "dragon123",
    "trustno1", "abc12345", "passw0rd", "qwertyuiop", "1q2w3e4r",
}


def generate_otp() -> str:
    """A cryptographically random numeric code, zero-padded to OTP_LENGTH digits."""
    upper = 10**settings.OTP_LENGTH
    return str(secrets.randbelow(upper)).zfill(settings.OTP_LENGTH)


def hash_otp(code: str) -> str:
    return bcrypt.hashpw(code.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_otp_hash(code: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(code.encode("utf-8"), hashed.encode("ascii"))
    except ValueError:
        return False


async def create_otp(db: AsyncSession, email: str, purpose: str) -> str:
    """Invalidate any prior unconsumed OTP for this email+purpose and issue a new one.

    Returns the plaintext code so the caller can email it immediately - it is
    never returned again or stored anywhere but as a hash.
    """
    email = email.strip().lower()
    existing = await db.execute(
        select(EmailOTP).where(
            EmailOTP.email == email,
            EmailOTP.purpose == purpose,
            EmailOTP.consumed_at.is_(None),
        )
    )
    now = datetime.now(UTC)
    for row in existing.scalars().all():
        row.consumed_at = now  # supersede - prevents stacking multiple live codes

    code = generate_otp()
    otp_row = EmailOTP(
        email=email,
        purpose=purpose,
        otp_hash=hash_otp(code),
        max_attempts=settings.OTP_MAX_ATTEMPTS,
        expires_at=now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
    )
    db.add(otp_row)
    await db.commit()
    return code


class OTPVerifyResult:
    def __init__(self, ok: bool, reason: str | None = None):
        self.ok = ok
        self.reason = reason  # "not_found" | "expired" | "too_many_attempts" | "invalid"


async def verify_otp(db: AsyncSession, email: str, purpose: str, code: str) -> OTPVerifyResult:
    """Check `code` against the latest unconsumed OTP for email+purpose.

    Every call that finds a live row commits its attempt-count/consumed
    changes immediately, so brute-force and replay are enforced even if the
    caller's own transaction later fails for an unrelated reason.
    """
    email = email.strip().lower()
    res = await db.execute(
        select(EmailOTP)
        .where(
            EmailOTP.email == email,
            EmailOTP.purpose == purpose,
            EmailOTP.consumed_at.is_(None),
        )
        .order_by(EmailOTP.created_at.desc())
        .limit(1)
    )
    otp_row = res.scalars().first()
    if not otp_row:
        return OTPVerifyResult(False, "not_found")

    now = datetime.now(UTC)
    expires_at = otp_row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if now > expires_at:
        otp_row.consumed_at = now
        await db.commit()
        return OTPVerifyResult(False, "expired")

    if otp_row.attempts >= otp_row.max_attempts:
        otp_row.consumed_at = now
        await db.commit()
        return OTPVerifyResult(False, "too_many_attempts")

    if not verify_otp_hash(code, otp_row.otp_hash):
        otp_row.attempts += 1
        if otp_row.attempts >= otp_row.max_attempts:
            otp_row.consumed_at = now
        await db.commit()
        return OTPVerifyResult(False, "invalid")

    otp_row.consumed_at = now
    await db.commit()
    return OTPVerifyResult(True)


class PasswordPolicyError(ValueError):
    def __init__(self, reasons: list[str]):
        self.reasons = reasons
        super().__init__("; ".join(reasons))


def validate_password_strength(password: str, email: str | None = None) -> None:
    """Raise PasswordPolicyError listing every rule the password violates.

    Backend-authoritative: this runs regardless of what the frontend already
    checked, since a client-side check can always be bypassed by calling the
    API directly.
    """
    reasons: list[str] = []
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        reasons.append(f"Must be at least {settings.PASSWORD_MIN_LENGTH} characters long")
    if not any(c.isupper() for c in password):
        reasons.append("Must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        reasons.append("Must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        reasons.append("Must contain at least one number")
    if not any(not c.isalnum() for c in password):
        reasons.append("Must contain at least one special character")
    if password.lower() in COMMON_PASSWORDS:
        reasons.append("This password is too common - choose something less predictable")
    if email:
        local_part = email.split("@")[0].lower()
        if local_part and local_part in password.lower():
            reasons.append("Password must not contain your email address")
    if reasons:
        raise PasswordPolicyError(reasons)


def is_account_locked(user) -> bool:
    if not user.locked_until:
        return False
    locked_until = user.locked_until
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=UTC)
    return datetime.now(UTC) < locked_until


async def record_failed_login(db: AsyncSession, user) -> None:
    """Increment the failed-attempt counter and lock the account if it crosses
    the configured threshold. Committed immediately so the lockout is
    enforced even if the caller's request otherwise fails afterward."""
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    if user.failed_login_attempts >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
        user.locked_until = datetime.now(UTC) + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
    await db.commit()


async def reset_failed_login(db: AsyncSession, user) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(UTC)
    await db.commit()
