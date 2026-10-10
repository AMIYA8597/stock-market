import logging
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_current_user_or_none
from app.core.otp import (
    PasswordPolicyError,
    create_otp,
    hash_password,
    is_account_locked,
    record_failed_login,
    reset_failed_login,
    validate_password_strength,
    verify_otp,
    verify_password,
)
from app.core.rate_limit import check_rate_limit
from app.core.security import ensure_personal_organization
from app.core.test_state import TEST_JWT_SECRET, is_test_mode
from app.database.connection import get_db
from app.models.identity import User
from app.schemas.errors import ErrorCode, ErrorDetail, ErrorResponse
from app.services.email_service import EmailDeliveryError, send_otp_email

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


# ─── Request/response models ────────────────────────────────────────────


class CheckEmailRequest(BaseModel):
    email: EmailStr


class CheckEmailResponse(BaseModel):
    exists: bool


class AuthRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class VerifySignupOTP(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=4, max_length=8)
    password: str


class ResendOTPRequest(BaseModel):
    email: EmailStr
    purpose: str = "signup"


class AuthLogin(BaseModel):
    email: EmailStr
    password: str


class AuthRefresh(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int = 3600


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=4, max_length=8)
    new_password: str


OTP_ERROR_MESSAGES: dict[str, str] = {
    "not_found": "No verification code found for this email. Please request a new one.",
    "expired": "This code has expired. Please request a new one.",
    "too_many_attempts": "Too many incorrect attempts. Please request a new code.",
    "invalid": "Incorrect verification code.",
}


def _otp_error(reason: str | None) -> HTTPException:
    status_code = 429 if reason == "too_many_attempts" else 400
    return HTTPException(status_code=status_code, detail=OTP_ERROR_MESSAGES.get(reason or "invalid", "Invalid code"))


async def _supabase_delete_user(auth_id: str) -> None:
    """Best-effort: delete a Supabase auth user by UUID. Silently ignores all errors."""
    async with httpx.AsyncClient() as client:
        try:
            await client.delete(
                f"{settings.SUPABASE_URL}/auth/v1/admin/users/{auth_id}",
                headers={
                    "apikey": settings.SUPABASE_SECRET_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SECRET_KEY}",
                },
            )
        except Exception:
            pass


async def _supabase_find_auth_id_by_email(email: str) -> str | None:
    """Look up a Supabase auth user UUID by email via the admin API. Returns None on any failure."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{settings.SUPABASE_URL}/auth/v1/admin/users",
                params={"filter": email, "page": 1, "per_page": 50},
                headers={
                    "apikey": settings.SUPABASE_SECRET_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SECRET_KEY}",
                },
            )
            if resp.status_code == 200:
                for u in (resp.json().get("users") or []):
                    if (u.get("email") or "").lower() == email:
                        return u.get("id")
        except Exception:
            pass
    return None


def _password_policy_error(exc: PasswordPolicyError) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail=ErrorResponse.create(
            code=ErrorCode.PASSWORD_TOO_WEAK,
            message="Password does not meet security requirements",
            details=[
                ErrorDetail(field="password", code=ErrorCode.PASSWORD_TOO_WEAK, message=reason)
                for reason in exc.reasons
            ],
        ).dict(),
    )


def _issue_test_token(user: User) -> TokenResponse:
    import jwt

    secret = settings.SUPABASE_JWT_SECRET or TEST_JWT_SECRET
    token = jwt.encode({"sub": str(user.auth_id), "type": "access", "aud": "authenticated"}, secret, algorithm="HS256")
    return TokenResponse(access_token=token, refresh_token="test_refresh")


# ─── Email existence check (drives the "Account not found" login UX) ───


@router.post("/check-email", response_model=CheckEmailResponse)
async def check_email(payload: CheckEmailRequest, request: Request, db: AsyncSession = Depends(get_db)):
    await check_rate_limit(f"check-email:{_client_ip(request)}", requests=30, window=60)
    email = payload.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    return CheckEmailResponse(exists=result.scalars().first() is not None)


# ─── Registration + signup OTP ──────────────────────────────────────────


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: AuthRegister, request: Request, db: AsyncSession = Depends(get_db)):
    email = payload.email.strip().lower()
    await check_rate_limit(f"register:{_client_ip(request)}", requests=10, window=3600)

    try:
        validate_password_strength(payload.password, email=email)
    except PasswordPolicyError as exc:
        raise _password_policy_error(exc) from exc

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalars().first():
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists. Try signing in, or use Forgot Password.",
        )

    if is_test_mode():
        try:
            user = User(
                email=email,
                full_name=payload.full_name,
                auth_id=uuid.uuid4().hex,
                status="active",
                email_verified=False,
                password_hash=hash_password(payload.password),
            )
            db.add(user)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            raise HTTPException(status_code=409, detail="Email already registered") from exc
    else:
        # Before creating a new Supabase auth user, clean up any orphaned one
        # (a previous signup where local DB commit or OTP email failed, leaving
        # a Supabase auth record with no matching local row).
        orphan_auth_id = await _supabase_find_auth_id_by_email(email)
        if orphan_auth_id:
            await _supabase_delete_user(orphan_auth_id)

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    f"{settings.SUPABASE_URL}/auth/v1/signup",
                    json={"email": email, "password": payload.password},
                    headers={"apikey": settings.SUPABASE_SECRET_KEY},
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                try:
                    detail = e.response.json().get("msg") or e.response.json().get("error_description")
                except Exception:
                    detail = None
                raise HTTPException(status_code=400, detail=detail or "Registration failed") from e
            except httpx.HTTPError as e:
                raise HTTPException(status_code=502, detail="Could not reach the auth service") from e

            data = resp.json()
            logger.info("supabase_signup_response status=%s body=%s", resp.status_code, data)

            # Supabase GoTrue signup responses:
            # - New user: {user: {id: "...", identities: [...], ...}}
            # - Existing confirmed user: {user: {id: "...", identities: [], ...}} or {user: null}
            # - Existing unconfirmed: returns the user again (re-sends confirmation)
            user_obj = data if isinstance(data, dict) and "id" in data else (data.get("user") or {})
            auth_id = user_obj.get("id")
            identities = user_obj.get("identities")

            if not auth_id:
                # Supabase still returned user:null despite orphan cleanup — the
                # account is genuinely confirmed and in active use.
                raise HTTPException(
                    status_code=409,
                    detail="An account with this email already exists. Try signing in, or use Forgot Password.",
                )

            if isinstance(identities, list) and len(identities) == 0:
                raise HTTPException(
                    status_code=409,
                    detail="An account with this email already exists. Try signing in, or use Forgot Password.",
                )

            try:
                user = User(
                    email=email,
                    full_name=payload.full_name,
                    auth_id=auth_id,
                    status="active",
                    email_verified=False,
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)
            except Exception:
                await db.rollback()
                # Local insert failed — roll back Supabase too so no orphan is created.
                await _supabase_delete_user(auth_id)
                raise HTTPException(
                    status_code=500,
                    detail="Registration failed due to a server error. Please try again.",
                ) from None

    await ensure_personal_organization(db, user)

    # If SendGrid is not configured, skip OTP and auto-verify the account.
    if not settings.SENDGRID_API_KEY:
        user.email_verified = True
        await db.commit()
        async with httpx.AsyncClient() as client:
            try:
                await client.put(
                    f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user.auth_id}",
                    json={"email_confirm": True},
                    headers={
                        "apikey": settings.SUPABASE_SECRET_KEY,
                        "Authorization": f"Bearer {settings.SUPABASE_SECRET_KEY}",
                    },
                )
            except httpx.HTTPError as exc:
                logger.warning(f"Failed to confirm Supabase email for {user.id}: {exc}")
            try:
                resp = await client.post(
                    f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
                    json={"email": email, "password": payload.password},
                    headers={"apikey": settings.SUPABASE_SECRET_KEY},
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                raise HTTPException(
                    status_code=401,
                    detail="Account created. Please log in manually.",
                ) from exc
        await reset_failed_login(db, user)
        return TokenResponse(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token"),
            expires_in=data.get("expires_in", 3600),
        )

    code = await create_otp(db, email, "signup")
    try:
        await send_otp_email(email, code, "signup")
    except EmailDeliveryError as exc:
        # OTP email send failed — roll back the local user row and the Supabase auth
        # user so the person can retry registration cleanly once email is working.
        try:
            await db.delete(user)
            await db.commit()
        except Exception:
            await db.rollback()
        if not is_test_mode():
            await _supabase_delete_user(user.auth_id)
        raise HTTPException(
            status_code=503,
            detail="Could not send verification email. Please try again later.",
        ) from exc

    return {"email": email, "message": "Verification code sent to your email."}


@router.post("/verify-signup-otp", response_model=TokenResponse)
async def verify_signup_otp(payload: VerifySignupOTP, request: Request, db: AsyncSession = Depends(get_db)):
    email = payload.email.strip().lower()
    await check_rate_limit(f"verify-otp:{email}", requests=10, window=600)

    result = await verify_otp(db, email, "signup", payload.otp)
    if not result.ok:
        raise _otp_error(result.reason)

    user_result = await db.execute(select(User).where(User.email == email))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")

    user.email_verified = True
    await db.commit()
    await ensure_personal_organization(db, user)

    if is_test_mode():
        if not user.password_hash or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Verified, but automatic sign-in failed. Please log in manually.")
        await reset_failed_login(db, user)
        return _issue_test_token(user)

    async with httpx.AsyncClient() as client:
        # Best-effort: keep Supabase's own confirmation state consistent too.
        # Our local email_verified flag (checked by /auth/login and
        # get_current_context) is what actually gates access either way.
        try:
            await client.put(
                f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user.auth_id}",
                json={"email_confirm": True},
                headers={
                    "apikey": settings.SUPABASE_SECRET_KEY,
                    "Authorization": f"Bearer {settings.SUPABASE_SECRET_KEY}",
                },
            )
        except httpx.HTTPError as exc:
            logger.warning(f"Failed to mark Supabase email confirmed for user {user.id}: {exc}")

        try:
            resp = await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
                json={"email": email, "password": payload.password},
                headers={"apikey": settings.SUPABASE_SECRET_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            raise HTTPException(
                status_code=401,
                detail="Verified, but automatic sign-in failed. Please log in manually.",
            ) from exc

    await reset_failed_login(db, user)
    return TokenResponse(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_in=data.get("expires_in", 3600),
    )


@router.post("/resend-otp", status_code=status.HTTP_202_ACCEPTED)
async def resend_otp(payload: ResendOTPRequest, request: Request, db: AsyncSession = Depends(get_db)):
    email = payload.email.strip().lower()
    if payload.purpose not in {"signup", "password_reset"}:
        raise HTTPException(status_code=400, detail="Invalid purpose")

    await check_rate_limit(f"resend-otp:{email}", requests=3, window=3600)

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    # Same response regardless of whether the account exists or is already
    # verified, so this endpoint can't be used to probe account existence.
    if user and (payload.purpose == "password_reset" or not user.email_verified):
        code = await create_otp(db, email, payload.purpose)
        try:
            await send_otp_email(email, code, payload.purpose)
        except EmailDeliveryError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {"message": "If a verification code can be sent to that address, it's on its way."}


# ─── Login ───────────────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
async def login(payload: AuthLogin, request: Request, db: AsyncSession = Depends(get_db)):
    email = payload.email.strip().lower()
    await check_rate_limit(f"login:{_client_ip(request)}", requests=20, window=60)

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Account not found. Please register your account first.")

    if is_account_locked(user):
        raise HTTPException(
            status_code=429,
            detail=ErrorResponse.create(
                code=ErrorCode.ACCOUNT_LOCKED,
                message="Account locked due to too many failed attempts. Try again in a few minutes, or reset your password.",
            ).dict(),
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before signing in. Check your inbox for the verification code, or request a new one.",
        )

    invalid_credentials = HTTPException(
        status_code=401,
        detail=ErrorResponse.create(code=ErrorCode.INVALID_CREDENTIALS, message="Incorrect password.").dict(),
    )

    if is_test_mode():
        if not user.password_hash or not verify_password(payload.password, user.password_hash):
            await record_failed_login(db, user)
            raise invalid_credentials
        await reset_failed_login(db, user)
        return _issue_test_token(user)

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=password",
                json={"email": email, "password": payload.password},
                headers={"apikey": settings.SUPABASE_SECRET_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            await record_failed_login(db, user)
            raise invalid_credentials from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail="Could not reach the auth service. Please try again.") from exc

    await reset_failed_login(db, user)
    return TokenResponse(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_in=data.get("expires_in", 3600),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: AuthRefresh, db: AsyncSession = Depends(get_db)):
    if is_test_mode():
        result = await db.execute(select(User))
        user = result.scalars().first()
        import uuid as _uuid

        import jwt

        secret = settings.SUPABASE_JWT_SECRET or TEST_JWT_SECRET
        token = jwt.encode(
            {"sub": str(user.auth_id) if user and hasattr(user, "auth_id") else "test", "type": "access", "jti": str(_uuid.uuid4())},
            secret,
            algorithm="HS256",
        )
        return TokenResponse(access_token=token, refresh_token="test_refresh_new")

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{settings.SUPABASE_URL}/auth/v1/token?grant_type=refresh_token",
                json={"refresh_token": payload.refresh_token},
                headers={"apikey": settings.SUPABASE_SECRET_KEY},
            )
            resp.raise_for_status()
            data = resp.json()
            return TokenResponse(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                expires_in=data.get("expires_in", 3600),
            )
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Invalid refresh token") from exc


# ─── Forgot / reset password ─────────────────────────────────────────────


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(payload: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    email = payload.email.strip().lower()
    await check_rate_limit(f"forgot-password:{email}", requests=3, window=3600)

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if user:
        code = await create_otp(db, email, "password_reset")
        try:
            await send_otp_email(email, code, "password_reset")
        except EmailDeliveryError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    # Generic response regardless of whether the email is registered, so
    # this endpoint can't be used to enumerate accounts.
    return {"message": "If that email is registered, we've sent a password reset code."}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    email = payload.email.strip().lower()
    await check_rate_limit(f"reset-password:{email}", requests=10, window=600)

    try:
        validate_password_strength(payload.new_password, email=email)
    except PasswordPolicyError as exc:
        raise _password_policy_error(exc) from exc

    result = await verify_otp(db, email, "password_reset", payload.otp)
    if not result.ok:
        raise _otp_error(result.reason)

    user_result = await db.execute(select(User).where(User.email == email))
    user = user_result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Account not found")

    if is_test_mode():
        user.password_hash = hash_password(payload.new_password)
    else:
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.put(
                    f"{settings.SUPABASE_URL}/auth/v1/admin/users/{user.auth_id}",
                    json={"password": payload.new_password},
                    headers={
                        "apikey": settings.SUPABASE_SECRET_KEY,
                        "Authorization": f"Bearer {settings.SUPABASE_SECRET_KEY}",
                    },
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise HTTPException(status_code=502, detail="Could not reset password. Please try again.") from exc

    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()
    return {"message": "Password updated. You can now sign in with your new password."}


# ─── Session ──────────────────────────────────────────────────────────────

_test_logged_out_users = set()


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: User | None = Depends(get_current_user_or_none)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if is_test_mode():
        _test_logged_out_users.add(str(current_user.id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me")
async def me(current_user: User | None = Depends(get_current_user_or_none)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "status": current_user.status,
        "email_verified": current_user.email_verified,
    }


@router.get("/auth/upstox/login-url")
async def upstox_login_url():
    try:
        from app.services.upstox_service import UpstoxService
        url = UpstoxService.get_login_url()
        return {"login_url": url}
    except ValueError as e:
        return {"login_url": None, "error": str(e)}


@router.get("/auth/upstox/status")
async def upstox_auth_status():
    from app.services.upstox_service import UpstoxService
    return {
        "authenticated": UpstoxService.ACCESS_TOKEN is not None,
        "profile": UpstoxService.USER_PROFILE,
        "connection_status": UpstoxService.CONNECTION_STATUS,
    }


@router.get("/auth/upstox/callback")
async def upstox_callback(code: str | None = None, error: str | None = None):
    if error or not code:
        raise HTTPException(status_code=400, detail=error or "No authorization code received")
    try:
        from app.services.upstox_service import UpstoxService
        result = await UpstoxService.exchange_code_for_token(code)
        return {"success": True, "profile": result.get("user_profile")}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
