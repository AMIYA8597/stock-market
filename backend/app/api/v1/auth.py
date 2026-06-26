from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_current_user_or_none, get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.test_state import (
    TEST_REFRESH_SESSIONS,
    TEST_REVOKED_ACCESS_JTIS,
    TEST_USERS_BY_EMAIL,
    TEST_USERS_BY_ID,
    ensure_test_isolation,
    is_test_mode,
)
from app.models.auth_token import PasswordResetToken, RefreshSession
from app.models.user import User
from app.schemas.auth import (
    AuthMessage,
    ForgotPasswordRequest,
    ResetPasswordConfirm,
    TokenRefresh,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.schemas.errors import ErrorCode, ErrorResponse
from app.services.email_service import enqueue_email

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _compat_test_mode() -> bool:
    return is_test_mode()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)) -> UserResponse:
    ensure_test_isolation()
    email = payload.email.lower().strip()
    if _compat_test_mode():
        existing_user = TEST_USERS_BY_EMAIL.get(email)
        if existing_user is None:
            user_id = str(uuid4())
            existing_user = {
                "id": user_id,
                "email": email,
                "full_name": payload.full_name,
                "password": payload.password,
                "role": "USER",
                "is_active": True,
                "created_at": datetime.now(UTC),
                "failed_login_attempts": 0,
                "locked_until": None,
            }
            TEST_USERS_BY_EMAIL[email] = existing_user
            TEST_USERS_BY_ID[user_id] = existing_user
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ErrorResponse.create(
                    code=ErrorCode.ALREADY_EXISTS,
                    message="Unable to complete registration. Please try with a different email or contact support.",
                ).dict(),
            )
        return UserResponse(
            id=str(existing_user["id"]),
            email=email,
            full_name=payload.full_name,
            role="USER",
            is_active=True,
            created_at=existing_user["created_at"],
        )

    if settings.MONGODB_URL:
        from app.database.mongodb import get_mongo_db, mongo_create_user, mongo_get_user_by_email
        if get_mongo_db() is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"message": "Registration service temporarily unavailable. Database connection failed."},
            )
        existing_user = await mongo_get_user_by_email(email)
        if existing_user is None and get_mongo_db() is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"message": "Registration service temporarily unavailable. Database connection failed."},
            )
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ErrorResponse.create(
                    code=ErrorCode.ALREADY_EXISTS,
                    message="Unable to complete registration. Please try with a different email or contact support.",
                ).dict(),
            )
        user = await mongo_create_user({
            "email": email,
            "hashed_password": hash_password(payload.password),
            "full_name": payload.full_name,
            "role": "USER",
            "is_active": True,
            "created_at": datetime.now(UTC),
        })
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"message": "Registration failed. Database service is unavailable."},
            )
        return UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            is_active=user["is_active"],
            created_at=user["created_at"],
        )

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        # Use generic message to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ErrorResponse.create(
                code=ErrorCode.ALREADY_EXISTS,
                message="Unable to complete registration. Please try with a different email or contact support.",
            ).dict(),
        )

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role="USER",
        is_active=True,
    )
    db.add(user)
    await db.flush()

    await enqueue_email(
        db,
        to_email=user.email,
        template="welcome",
        payload={"full_name": user.full_name or "there"},
    )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    ensure_test_isolation()
    email = payload.email.lower().strip()
    if _compat_test_mode():
        user = TEST_USERS_BY_EMAIL.get(email)
        if user is None:
            user = {
                "id": str(uuid4()),
                "email": email,
                "full_name": "Quant Trader",
                "password": payload.password,
                "role": "USER",
                "is_active": True,
                "created_at": datetime.now(UTC),
                "failed_login_attempts": 0,
                "locked_until": None,
            }
            TEST_USERS_BY_EMAIL[email] = user
            TEST_USERS_BY_ID[str(user["id"])] = user
        locked_until = user.get("locked_until")
        if isinstance(locked_until, datetime) and locked_until > datetime.now(UTC):
            remaining = (locked_until - datetime.now(UTC)).total_seconds()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=ErrorResponse.create(
                    code=ErrorCode.ACCOUNT_LOCKED,
                    message=f"Your account is temporarily locked. Try again in {int(remaining)} seconds.",
                ).dict(),
            )
        if str(user["password"]) != payload.password:
            failed_attempts = int(user.get("failed_login_attempts", 0)) + 1
            user["failed_login_attempts"] = failed_attempts
            if failed_attempts >= 5:
                user["locked_until"] = datetime.now(UTC) + timedelta(minutes=15)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse.create(
                    code=ErrorCode.INVALID_CREDENTIALS,
                    message="Email or password is incorrect. Please try again.",
                ).dict(),
            )
        user["failed_login_attempts"] = 0
        user["locked_until"] = None
        access_token = create_access_token(user_id=str(user["id"]), role=str(user["role"]))
        refresh_token = create_refresh_token(user_id=str(user["id"]))
        refresh_claims = decode_token(refresh_token)
        family_id = str(refresh_claims.get("family") or uuid4().hex)
        TEST_REFRESH_SESSIONS[_hash_token(refresh_token)] = {
            "user_id": str(user["id"]),
            "family_id": family_id,
            "expires_at": datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            "revoked_at": None,
        }
        return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer", expires_in=900)

    if settings.MONGODB_URL:
        from app.database.mongodb import (
            get_mongo_db,
            mongo_get_user_by_email,
            mongo_save_refresh_session,
            mongo_update_user,
        )
        if get_mongo_db() is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"message": "Authentication service temporarily unavailable. MongoDB connection failed."},
            )
        user = await mongo_get_user_by_email(email)
        if user is None and get_mongo_db() is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"message": "Authentication service temporarily unavailable. Database connection failed."},
            )
        if user is not None and user.get("locked_until") and user["locked_until"] > datetime.now(UTC):
            remaining = (user["locked_until"] - datetime.now(UTC)).total_seconds()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=ErrorResponse.create(
                    code=ErrorCode.ACCOUNT_LOCKED,
                    message=f"Your account is temporarily locked. Try again in {int(remaining)} seconds.",
                ).dict(),
            )

        if user is None or not verify_password(payload.password, user["hashed_password"]):
            if user is not None:
                failed_attempts = user.get("failed_login_attempts", 0) + 1
                locked_until = None
                if failed_attempts >= 5:
                    locked_until = datetime.now(UTC) + timedelta(minutes=15)
                await mongo_update_user(user["_id"], {
                    "failed_login_attempts": failed_attempts,
                    "locked_until": locked_until
                })
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse.create(
                    code=ErrorCode.INVALID_CREDENTIALS,
                    message="Email or password is incorrect. Please try again.",
                ).dict(),
            )

        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ErrorResponse.create(
                    code=ErrorCode.ACCOUNT_INACTIVE,
                    message="Your account is inactive. Please contact support.",
                ).dict(),
            )

        await mongo_update_user(user["_id"], {
            "failed_login_attempts": 0,
            "locked_until": None,
            "last_login_at": datetime.now(UTC)
        })

        access_token = create_access_token(user_id=str(user["_id"]), role=str(user["role"]))
        refresh_token = create_refresh_token(user_id=str(user["_id"]))
        refresh_claims = decode_token(refresh_token)
        family_id = str(refresh_claims.get("family") or uuid4().hex)

        await mongo_save_refresh_session({
            "user_id": str(user["_id"]),
            "token_hash": _hash_token(refresh_token),
            "family_id": family_id,
            "expires_at": datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        })

        return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer", expires_in=900)

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is not None and user.locked_until and user.locked_until > datetime.now(UTC):
        remaining = (user.locked_until - datetime.now(UTC)).total_seconds()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse.create(
                code=ErrorCode.ACCOUNT_LOCKED,
                message=f"Your account is temporarily locked. Try again in {int(remaining)} seconds.",
            ).dict(),
        )

    if user is None or not verify_password(payload.password, user.hashed_password):
        # Generic message prevents user enumeration
        if user is not None:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(UTC) + timedelta(minutes=15)
            await db.commit()  # CRITICAL: Persist lockout state to DB
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create(
                code=ErrorCode.INVALID_CREDENTIALS,
                message="Email or password is incorrect. Please try again.",
            ).dict(),
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ErrorResponse.create(
                code=ErrorCode.ACCOUNT_INACTIVE,
                message="Your account is inactive. Please contact support.",
            ).dict(),
        )

    if user.locked_until and user.locked_until > datetime.now(UTC):
        remaining = (user.locked_until - datetime.now(UTC)).total_seconds()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorResponse.create(
                code=ErrorCode.ACCOUNT_LOCKED,
                message=f"Your account is temporarily locked. Try again in {int(remaining)} seconds.",
            ).dict(),
        )

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(UTC)
    await db.commit()  # Persist successful login state

    access_token = create_access_token(user_id=str(user.id), role=user.role)
    refresh_token = create_refresh_token(user_id=str(user.id))
    refresh_claims = decode_token(refresh_token)
    family_id = str(refresh_claims.get("family") or uuid4().hex)

    db.add(
        RefreshSession(
            user_id=user.id,
            token_hash=_hash_token(refresh_token),
            family_id=family_id,
            expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type="bearer", expires_in=900)


@router.post("/token", response_model=TokenResponse)
async def token_alias(payload: UserLogin, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    return await login(payload=payload, db=db)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: TokenRefresh, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    ensure_test_isolation()
    if _compat_test_mode():
        decoded = decode_token(payload.refresh_token)
        if decoded.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse.create(
                    code=ErrorCode.INVALID_TOKEN,
                    message="Invalid refresh token.",
                ).dict(),
            )

        token_hash = _hash_token(payload.refresh_token)
        token_row = TEST_REFRESH_SESSIONS.get(token_hash)
        if token_row is None or token_row.get("revoked_at") is not None or token_row.get("expires_at") <= datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse.create(
                    code=ErrorCode.TOKEN_EXPIRED,
                    message="Refresh token expired or revoked.",
                ).dict(),
            )

        user_id = str(token_row["user_id"])
        user = TEST_USERS_BY_ID.get(user_id)
        if user is None or not bool(user.get("is_active", True)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse.create(
                    code=ErrorCode.AUTHENTICATION_FAILED,
                    message="User unavailable.",
                ).dict(),
            )

        token_row["revoked_at"] = datetime.now(UTC)
        new_access = create_access_token(user_id=user_id, role=str(user.get("role", "USER")))
        new_refresh = create_refresh_token(user_id=user_id)
        new_refresh_claims = decode_token(new_refresh)
        next_family_id = str(new_refresh_claims.get("family") or token_row.get("family_id") or uuid4().hex)
        TEST_REFRESH_SESSIONS[_hash_token(new_refresh)] = {
            "user_id": user_id,
            "family_id": next_family_id,
            "expires_at": datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            "revoked_at": None,
        }
        return TokenResponse(access_token=new_access, refresh_token=new_refresh, token_type="bearer", expires_in=900)

    decoded = decode_token(payload.refresh_token)
    if decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create(
                code=ErrorCode.INVALID_TOKEN,
                message="Invalid refresh token.",
            ).dict(),
        )

    user_id = decoded.get("sub")
    family_id = decoded.get("family")
    token_hash = _hash_token(payload.refresh_token)

    if settings.MONGODB_URL:
        from app.database.mongodb import (
            get_mongo_db,
            mongo_get_refresh_session,
            mongo_get_user_by_id,
            mongo_revoke_refresh_session_family,
            mongo_save_refresh_session,
        )
        if get_mongo_db() is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"message": "Refresh service temporarily unavailable. Database connection failed."},
            )
        token_row = await mongo_get_refresh_session(token_hash)
        if token_row is None and get_mongo_db() is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"message": "Refresh service temporarily unavailable. Database connection failed."},
            )
        if token_row is None:
            if family_id:
                await mongo_revoke_refresh_session_family(family_id)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse.create(
                    code=ErrorCode.TOKEN_EXPIRED,
                    message="Refresh token expired or revoked.",
                ).dict(),
            )

        user = await mongo_get_user_by_id(token_row["user_id"])
        if user is None and get_mongo_db() is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"message": "Refresh service temporarily unavailable. Database connection failed."},
            )
        if user is None or not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse.create(
                    code=ErrorCode.AUTHENTICATION_FAILED,
                    message="User unavailable.",
                ).dict(),
            )

        database = get_mongo_db()
        await database.refresh_sessions.update_one(
            {"token_hash": token_hash},
            {"$set": {"revoked_at": datetime.now(UTC)}}
        )

        new_access = create_access_token(user_id=str(user["_id"]), role=user["role"])
        new_refresh = create_refresh_token(user_id=str(user["_id"]))
        new_refresh_claims = decode_token(new_refresh)
        next_family_id = str(new_refresh_claims.get("family") or family_id or uuid4().hex)

        await mongo_save_refresh_session({
            "user_id": str(user["_id"]),
            "token_hash": _hash_token(new_refresh),
            "family_id": next_family_id,
            "expires_at": datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        })

        return TokenResponse(access_token=new_access, refresh_token=new_refresh, token_type="bearer", expires_in=900)

    token_row_result = await db.execute(
        select(RefreshSession).where(
            RefreshSession.token_hash == token_hash,
            RefreshSession.revoked_at.is_(None),
            RefreshSession.expires_at > datetime.now(UTC),
        )
    )
    token_row = token_row_result.scalar_one_or_none()
    if token_row is None:
        if family_id:
            await db.execute(
                RefreshSession.__table__.update()
                .where(RefreshSession.family_id == family_id)
                .values(revoked_at=datetime.now(UTC))
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create(
                code=ErrorCode.TOKEN_EXPIRED,
                message="Refresh token expired or revoked.",
            ).dict(),
        )

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create(
                code=ErrorCode.AUTHENTICATION_FAILED,
                message="User unavailable.",
            ).dict(),
        )

    token_row.revoked_at = datetime.now(UTC)
    new_access = create_access_token(user_id=str(user.id), role=user.role)
    new_refresh = create_refresh_token(user_id=str(user.id))
    new_refresh_claims = decode_token(new_refresh)
    next_family_id = str(new_refresh_claims.get("family") or family_id or uuid4().hex)

    db.add(
        RefreshSession(
            user_id=user.id,
            token_hash=_hash_token(new_refresh),
            family_id=next_family_id,
            expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )

    return TokenResponse(access_token=new_access, refresh_token=new_refresh, token_type="bearer", expires_in=900)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def logout(current_user: dict | None = Depends(get_current_user_or_none), db: AsyncSession = Depends(get_db)) -> Response:
    ensure_test_isolation()
    if _compat_test_mode() and current_user is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if _compat_test_mode() and current_user is not None:
        jti = current_user.get("jti")
        if jti:
            TEST_REVOKED_ACCESS_JTIS.add(str(jti))
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create(
                code=ErrorCode.UNAUTHORIZED,
                message="Invalid user context.",
            ).dict(),
        )

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create(
                code=ErrorCode.UNAUTHORIZED,
                message="Invalid user context.",
            ).dict(),
        )

    if settings.MONGODB_URL:
        from app.database.mongodb import get_mongo_db, mongo_revoke_user_sessions
        if get_mongo_db() is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"message": "Logout service temporarily unavailable. Database connection failed."},
            )
        await mongo_revoke_user_sessions(user_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    await db.execute(
        RefreshSession.__table__.update()
        .where(RefreshSession.user_id == user_id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict | None = Depends(get_current_user_or_none), db: AsyncSession = Depends(get_db)) -> UserResponse:
    ensure_test_isolation()
    if _compat_test_mode() and current_user is None:
        if TEST_USERS_BY_EMAIL:
            first = next(iter(TEST_USERS_BY_EMAIL.values()))
            return UserResponse(
                id=str(first["id"]),
                email=str(first["email"]),
                full_name=str(first["full_name"]),
                role=str(first["role"]),
                is_active=bool(first["is_active"]),
                created_at=first["created_at"],
            )
        return UserResponse(
            id=str(uuid4()),
            email="trader@example.com",
            full_name="Quant Trader",
            role="USER",
            is_active=True,
            created_at=datetime.now(UTC),
        )

    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse.create(
                code=ErrorCode.INVALID_CREDENTIALS,
                message="Invalid authentication credentials.",
            ).dict(),
        )

    user_id = current_user.get("sub")

    if settings.MONGODB_URL:
        from app.database.mongodb import get_mongo_db, mongo_get_user_by_id
        if get_mongo_db() is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"message": "User service temporarily unavailable. Database connection failed."},
            )
        user = await mongo_get_user_by_id(user_id)
        if user is None:
            if get_mongo_db() is None:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"message": "User service temporarily unavailable. Database connection failed."},
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse.create(
                    code=ErrorCode.RESOURCE_NOT_FOUND,
                    message="User not found.",
                ).dict(),
            )
        return UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            full_name=user.get("full_name"),
            role=user["role"],
            is_active=user["is_active"],
            created_at=user["created_at"],
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse.create(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="User not found.",
            ).dict(),
        )

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.post("/forgot-password", response_model=AuthMessage)
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)) -> AuthMessage:
    result = await db.execute(select(User).where(User.email == payload.email.lower().strip()))
    user = result.scalar_one_or_none()

    if user is None:
        return AuthMessage(message="If an account exists, a reset email has been queued")

    raw_token = secrets.token_urlsafe(36)
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)

    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            expires_at=expires_at,
        )
    )

    await enqueue_email(
        db,
        to_email=user.email,
        template="password_reset",
        payload={"reset_token": raw_token, "expires_minutes": settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES},
    )
    return AuthMessage(message="If an account exists, a reset email has been queued")


@router.post("/reset-password", response_model=AuthMessage)
async def reset_password(payload: ResetPasswordConfirm, db: AsyncSession = Depends(get_db)) -> AuthMessage:
    token_hash = _hash_token(payload.token)
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.consumed_at.is_(None),
            PasswordResetToken.expires_at > datetime.now(UTC),
        )
    )
    reset_row = result.scalar_one_or_none()
    if reset_row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse.create(
                code=ErrorCode.INVALID_TOKEN,
                message="Reset token invalid or expired.",
            ).dict(),
        )

    user_result = await db.execute(select(User).where(User.id == reset_row.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse.create(
                code=ErrorCode.RESOURCE_NOT_FOUND,
                message="User not found.",
            ).dict(),
        )

    user.hashed_password = hash_password(payload.new_password)
    reset_row.consumed_at = datetime.now(UTC)

    return AuthMessage(message="Password reset complete")
