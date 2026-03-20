"""
Authentication endpoints with enterprise security: RS256 JWT, 2FA, refresh token management.

Implements OAuth2 with Password flow + TOTP 2FA + backup codes.
- Access tokens: 15-minute expiry, RS256 signed
- Refresh tokens: 7-day expiry, stored in DB with family tracking
- Passwords: Argon2id hashed
- 2FA: TOTP with backup codes
- Field encryption: AES-256-GCM for sensitive data
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import uuid4

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    TokenType,
    create_token,
    decode_token,
    decrypt_field,
    encrypt_field,
    generate_totp_secret,
    get_current_active_user,
    get_current_user,
    get_totp_uri,
    hash_email,
    hash_password,
    require_role,
    verify_password,
    verify_totp_code,
)

settings = get_settings()
from app.models.user import BackupCode, RefreshToken, User
from app.schemas.auth import (
    BackupCodesResponse,
    ChangePassword,
    Disable2FA,
    Enable2FA,
    MessageResponse,
    ResetPasswordConfirm,
    ResetPasswordRequest,
    TokenRefresh,
    TokenResponse,
    TOTPSetupResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    Verify2FA,
)

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegister,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Register a new user account.

    - Validates email uniqueness
    - Hashes password with Argon2id
    - Encrypts email field
    - Assigns default role 'ANALYST'
    """
    email_hash = hash_email(payload.email)

    # Check if email already exists
    result = await db.execute(select(User).where(User.email_hash == email_hash))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=encrypt_field(payload.email),
        email_hash=email_hash,
        password_hash=hash_password(payload.password),
        role="ANALYST",
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        email=payload.email,  # Return unencrypted for confirmation
        role=user.role,
        is_active=user.is_active,
        is_2fa_enabled=user.is_2fa_enabled,
        email_verified_at=user.email_verified_at,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: UserLogin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Authenticate user and issue JWT token pair.

    - Verifies password with Argon2id
    - Handles 2FA if enabled
    - Issues access (15min) + refresh (7day) tokens
    - Stores refresh token in DB with family tracking
    """
    email_hash = hash_email(payload.email)

    result = await db.execute(select(User).where(User.email_hash == email_hash))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked due to failed login attempts",
        )

    # Reset failed attempts on successful login
    user.failed_login_attempts = 0
    user.last_login_at = datetime.now(timezone.utc)

    if user.is_2fa_enabled:
        if not payload.totp_code and not payload.backup_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="2FA required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        totp_secret = decrypt_field(user.totp_secret)
        if payload.totp_code and verify_totp_code(totp_secret, payload.totp_code):
            pass
        elif payload.backup_code:
            backup_result = await db.execute(
                select(BackupCode).where(
                    BackupCode.user_id == user.id,
                    BackupCode.used_at.is_(None),
                )
            )
            backup_codes = backup_result.scalars().all()
            valid_backup = False
            for code in backup_codes:
                if bcrypt.checkpw(payload.backup_code.encode(), code.code_hash.encode()):
                    code.used_at = datetime.now(timezone.utc)
                    valid_backup = True
                    break
            if not valid_backup:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid backup code",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code",
            )

    jti = str(uuid4())
    family_id = str(uuid4())

    access_token = create_token(
        user.id, TokenType.ACCESS, jti=jti, role=user.role, family_id=family_id
    )
    refresh_token = create_token(
        user.id, TokenType.REFRESH, jti=jti, family_id=family_id
    )

    refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    db_refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=refresh_token_hash,
        family_id=family_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(db_refresh_token)

    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=900,
    )


@router.post("/token", response_model=TokenResponse)
async def token_login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """OAuth2 password-flow token endpoint alias.

    This keeps `/auth/token` available per build prompt while reusing
    the same login verification and token issuance path.
    """
    payload = UserLogin(email=form_data.username, password=form_data.password)
    return await login(payload=payload, db=db)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: TokenRefresh,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Refresh an access token using a valid refresh token.

    Implements refresh token rotation with family tracking. If a refresh token
    is reused, the entire family is revoked to prevent replay attacks.
    """

    token_data = decode_token(payload.refresh_token)
    if token_data.get("type") != TokenType.REFRESH.value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type — expected refresh token",
        )

    user_id = token_data.get("sub")
    jti = token_data.get("jti")
    family_id = token_data.get("fid")

    refresh_token_hash = hashlib.sha256(payload.refresh_token.encode()).hexdigest()

    db_refresh_token = (
        (await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.token_hash == refresh_token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        ))
        .scalar_one_or_none()
    )

    if not db_refresh_token:
        # Token not found: possible reuse. Revoke entire family if known.
        if family_id:
            await db.execute(
                RefreshToken.__table__.update()
                .where(RefreshToken.family_id == family_id)
                .values(revoked_at=datetime.now(timezone.utc))
            )
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Verify user still exists and is active
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Revoke old refresh token
    db_refresh_token.revoked_at = datetime.now(timezone.utc)

    # Rotate tokens within same family
    new_jti = str(uuid4())
    access_token = create_token(
        user.id,
        TokenType.ACCESS,
        jti=new_jti,
        role=user.role,
        family_id=family_id,
    )
    new_refresh_token = create_token(
        user.id,
        TokenType.REFRESH,
        jti=new_jti,
        family_id=family_id,
    )

    new_refresh_token_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()
    new_db_refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=new_refresh_token_hash,
        family_id=family_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(new_db_refresh_token)

    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=900,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: Annotated[User, Depends(get_current_active_user)],
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Logout the current session by revoking tokens."""
    payload = decode_token(token)
    jti = payload.get("jti")
    if jti:
        await blacklist_jti(jti, expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)

    # Revoke all refresh tokens for the user
    await db.execute(
        RefreshToken.__table__.update()
        .where(RefreshToken.user_id == current_user.id)
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    """Get the currently authenticated user's profile."""
    return UserResponse(
        id=current_user.id,
        email=decrypt_field(current_user.email),  # Decrypt for display
        role=current_user.role,
        is_active=current_user.is_active,
        is_2fa_enabled=current_user.is_2fa_enabled,
        email_verified_at=current_user.email_verified_at,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
    )


@router.post("/2fa/setup", response_model=TOTPSetupResponse)
async def setup_2fa(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Set up TOTP 2FA for the current user."""
    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA already enabled",
        )

    secret = generate_totp_secret()
    email = decrypt_field(current_user.email)
    uri = get_totp_uri(secret, email)

    # Store encrypted secret temporarily (will be verified before enabling)
    current_user.totp_secret = encrypt_field(secret)

    await db.commit()

    return TOTPSetupResponse(
        secret=secret,
        uri=uri,
        qr_code_url=f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={uri}",
    )


@router.post("/2fa/verify", response_model=MessageResponse)
async def verify_2fa_setup(
    payload: Verify2FA,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Verify TOTP setup and enable 2FA."""
    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA already enabled",
        )

    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup not initiated",
        )

    secret = decrypt_field(current_user.totp_secret)
    if not verify_totp_code(secret, payload.totp_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code",
        )

    # Enable 2FA
    current_user.is_2fa_enabled = True

    # Generate backup codes
    backup_codes = []
    for _ in range(10):
        code = secrets.token_hex(4).upper()
        backup_codes.append(code)
        hashed_code = bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode()
        backup_code = BackupCode(
            user_id=current_user.id,
            code_hash=hashed_code,
        )
        db.add(backup_code)

    await db.commit()

    return MessageResponse(
        message="2FA enabled successfully",
        detail="Keep your backup codes safe: " + ", ".join(backup_codes),
    )


@router.get("/2fa/backup-codes", response_model=BackupCodesResponse)
async def get_backup_codes(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get unused backup codes."""
    result = await db.execute(
        select(BackupCode).where(
            BackupCode.user_id == current_user.id,
            BackupCode.used_at.is_(None)
        )
    )
    backup_codes = result.scalars().all()

    codes = []
    for code in backup_codes:
        # Note: In production, don't return plaintext codes
        # This is for demo purposes
        codes.append("BACKUP-" + str(code.id))

    return BackupCodesResponse(backup_codes=codes)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: ChangePassword,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Change user password."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password incorrect",
        )

    current_user.password_hash = hash_password(payload.new_password)
    await db.commit()

    return MessageResponse(message="Password changed successfully")
