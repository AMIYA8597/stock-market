"""
Authentication service with enterprise security features.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_logger import audit_logger
from app.core.config import settings
from app.core.rate_limiter import limiter
from app.core.security import (
    check_password_strength,
    check_pwned_password,
    create_access_token,
    create_refresh_token,
    decrypt_field,
    encrypt_field,
    generate_backup_codes,
    generate_totp_secret,
    get_totp_uri,
    hash_password,
    verify_backup_code,
    verify_password,
    verify_token,
    verify_totp_code,
)
from app.models.user import BackupCode, RefreshToken, User
from app.schemas.auth import (
    AuthResponse,
    BackupCodeVerify,
    EmailVerificationRequest,
    LoginRequest,
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    TOTPSetupResponse,
    TOTPVerify,
    TokenRefresh,
    UserCreate,
    UserResponse,
)

logger = structlog.get_logger()


class AuthService:
    """
    Authentication service handling all auth-related operations.
    """

    @staticmethod
    async def register_user(user_data: UserCreate, db: AsyncSession) -> AuthResponse:
        """
        Register a new user with validation and security checks.
        """
        try:
            # Check if user already exists
            result = await db.execute(
                select(User).where(User.email_hash == hash_password(user_data.email.lower()))
            )
            existing_user = result.scalar_one_or_none()

            if existing_user:
                return AuthResponse(
                    success=False,
                    message="User with this email already exists"
                )

            # Validate password strength
            password_check = check_password_strength(user_data.password)
            if not password_check["is_strong"]:
                return AuthResponse(
                    success=False,
                    message=f"Password too weak: {password_check['feedback']['warning']}"
                )

            # Check if password is pwned
            if await asyncio.get_event_loop().run_in_executor(
                None, check_pwned_password, user_data.password
            ):
                return AuthResponse(
                    success=False,
                    message="This password has been compromised. Please choose a different one."
                )

            # Create user
            user = User(
                email=encrypt_field(user_data.email.lower()),
                email_hash=hash_password(user_data.email.lower()),
                password_hash=hash_password(user_data.password),
                role=user_data.role,
            )

            db.add(user)
            await db.flush()  # Get user ID

            # Send verification email
            await AuthService._send_verification_email(user.email, user.id)

            # Audit log
            await audit_logger.log_event(
                "user_registered",
                user_id=str(user.id),
                details={"email": user_data.email, "role": user_data.role}
            )

            return AuthResponse(
                success=True,
                message="User registered successfully. Please check your email for verification.",
                data={"user_id": str(user.id)}
            )

        except Exception as e:
            logger.error("User registration failed", error=str(e))
            return AuthResponse(
                success=False,
                message="Registration failed. Please try again."
            )

    @staticmethod
    async def authenticate_user(
        login_data: LoginRequest,
        db: AsyncSession,
        client_ip: str,
        user_agent: str
    ) -> AuthResponse:
        """
        Authenticate user with comprehensive security checks.
        """
        try:
            # Rate limiting check
            rate_limit_result = await limiter.check_rate_limit(
                request=None,  # We'll handle this differently
                user_id=None,
                endpoint="auth/login"
            )

            if not rate_limit_result["allowed"]:
                return AuthResponse(
                    success=False,
                    message="Too many login attempts. Please try again later."
                )

            # Find user
            result = await db.execute(
                select(User).where(User.email_hash == hash_password(login_data.email.lower()))
            )
            user = result.scalar_one_or_none()

            if not user or not user.is_active:
                # Audit failed login
                await audit_logger.log_event(
                    "login_failed",
                    details={
                        "email": login_data.email,
                        "reason": "user_not_found_or_inactive",
                        "ip": client_ip,
                        "user_agent": user_agent
                    }
                )
                return AuthResponse(
                    success=False,
                    message="Invalid email or password"
                )

            # Check account lockout
            if user.locked_until and user.locked_until > datetime.now(timezone.utc):
                return AuthResponse(
                    success=False,
                    message="Account is temporarily locked due to too many failed attempts"
                )

            # Verify password
            if not verify_password(login_data.password, user.password_hash):
                # Increment failed attempts
                user.failed_login_attempts += 1

                # Lock account if too many failures
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)

                await db.commit()

                # Audit failed login
                await audit_logger.log_event(
                    "login_failed",
                    user_id=str(user.id),
                    details={
                        "reason": "invalid_password",
                        "attempts": user.failed_login_attempts,
                        "ip": client_ip,
                        "user_agent": user_agent
                    }
                )

                return AuthResponse(
                    success=False,
                    message="Invalid email or password"
                )

            # Check if 2FA is required
            if user.is_2fa_enabled:
                if not login_data.totp_code:
                    return AuthResponse(
                        success=False,
                        message="2FA code required",
                        data={"requires_2fa": True}
                    )

                # Verify TOTP
                if not verify_totp_code(user.totp_secret, login_data.totp_code):
                    await audit_logger.log_event(
                        "login_failed",
                        user_id=str(user.id),
                        details={
                            "reason": "invalid_2fa",
                            "ip": client_ip,
                            "user_agent": user_agent
                        }
                    )
                    return AuthResponse(
                        success=False,
                        message="Invalid 2FA code"
                    )

            # Reset failed attempts and update login time
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login_at = datetime.now(timezone.utc)
            await db.commit()

            # Create tokens
            access_token = create_access_token(subject=str(user.id))
            refresh_token_str = create_refresh_token(
                subject=str(user.id),
                family_id=secrets.token_urlsafe(16)
            )

            # Store refresh token
            refresh_token = RefreshToken(
                user_id=user.id,
                token_hash=hash_password(refresh_token_str),
                family_id=family_id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            )
            db.add(refresh_token)
            await db.commit()

            # Audit successful login
            await audit_logger.log_event(
                "login_successful",
                user_id=str(user.id),
                details={
                    "ip": client_ip,
                    "user_agent": user_agent,
                    "used_2fa": user.is_2fa_enabled
                }
            )

            user_response = UserResponse.from_orm(user)

            return AuthResponse(
                success=True,
                message="Login successful",
                data={
                    "token": {
                        "access_token": access_token,
                        "refresh_token": refresh_token_str,
                        "token_type": "bearer",
                        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                        "user": user_response.dict()
                    }
                }
            )

        except Exception as e:
            logger.error("Authentication failed", error=str(e))
            return AuthResponse(
                success=False,
                message="Authentication failed. Please try again."
            )

    @staticmethod
    async def refresh_access_token(
        refresh_data: TokenRefresh,
        db: AsyncSession,
        client_ip: str
    ) -> AuthResponse:
        """
        Refresh access token using refresh token.
        """
        try:
            # Verify refresh token
            payload = verify_token(refresh_data.refresh_token, "refresh")
            if not payload:
                return AuthResponse(
                    success=False,
                    message="Invalid refresh token"
                )

            user_id = payload["sub"]
            family_id = payload["family_id"]

            # Check if refresh token exists and is valid
            result = await db.execute(
                select(RefreshToken).where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.family_id == family_id,
                    RefreshToken.revoked_at.is_(None)
                )
            )
            stored_token = result.scalar_one_or_none()

            if not stored_token or stored_token.expires_at < datetime.now(timezone.utc):
                return AuthResponse(
                    success=False,
                    message="Refresh token expired or invalid"
                )

            # Rotate refresh token
            new_family_id = secrets.token_urlsafe(16)
            new_refresh_token_str = create_refresh_token(
                subject=user_id,
                family_id=new_family_id
            )

            # Revoke old token family
            await db.execute(
                update(RefreshToken).where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.family_id == family_id
                ).values(revoked_at=datetime.now(timezone.utc))
            )

            # Create new refresh token
            new_refresh_token = RefreshToken(
                user_id=user_id,
                token_hash=hash_password(new_refresh_token_str),
                family_id=new_family_id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            )
            db.add(new_refresh_token)

            # Create new access token
            access_token = create_access_token(subject=user_id)

            await db.commit()

            # Audit token refresh
            await audit_logger.log_event(
                "token_refreshed",
                user_id=user_id,
                details={"ip": client_ip}
            )

            return AuthResponse(
                success=True,
                message="Token refreshed successfully",
                data={
                    "token": {
                        "access_token": access_token,
                        "refresh_token": new_refresh_token_str,
                        "token_type": "bearer",
                        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
                    }
                }
            )

        except Exception as e:
            logger.error("Token refresh failed", error=str(e))
            return AuthResponse(
                success=False,
                message="Token refresh failed"
            )

    @staticmethod
    async def setup_totp(user_id: str, db: AsyncSession) -> AuthResponse:
        """
        Set up TOTP for user.
        """
        try:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user:
                return AuthResponse(success=False, message="User not found")

            secret = generate_totp_secret()
            user.totp_secret = encrypt_field(secret)
            await db.commit()

            # Get decrypted email for URI
            from app.core.security import decrypt_field
            email = decrypt_field(user.email)

            uri = get_totp_uri(secret, email)

            return AuthResponse(
                success=True,
                message="TOTP setup initiated",
                data={
                    "totp_setup": {
                        "secret": secret,
                        "qr_code_url": uri,
                        "backup_codes": generate_backup_codes()
                    }
                }
            )

        except Exception as e:
            logger.error("TOTP setup failed", error=str(e))
            return AuthResponse(
                success=False,
                message="TOTP setup failed"
            )

    @staticmethod
    async def verify_totp_setup(
        user_id: str,
        totp_data: TOTPVerify,
        backup_codes: list[str],
        db: AsyncSession
    ) -> AuthResponse:
        """
        Verify TOTP setup and enable 2FA.
        """
        try:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user or not user.totp_secret:
                return AuthResponse(success=False, message="TOTP not set up")

            from app.core.security import decrypt_field
            secret = decrypt_field(user.totp_secret)

            if not verify_totp_code(secret, totp_data.code):
                return AuthResponse(success=False, message="Invalid TOTP code")

            # Enable 2FA
            user.is_2fa_enabled = True

            # Store backup codes
            for code in backup_codes:
                backup_code = BackupCode(
                    user_id=user.id,
                    code_hash=hash_password(code)
                )
                db.add(backup_code)

            await db.commit()

            # Audit 2FA enable
            await audit_logger.log_event(
                "2fa_enabled",
                user_id=user_id
            )

            return AuthResponse(
                success=True,
                message="2FA enabled successfully"
            )

        except Exception as e:
            logger.error("TOTP verification failed", error=str(e))
            return AuthResponse(
                success=False,
                message="TOTP verification failed"
            )

    @staticmethod
    async def _send_verification_email(email: str, user_id: str):
        """
        Send email verification (placeholder - implement with SendGrid).
        """
        # TODO: Implement email sending
        logger.info("Email verification would be sent", email=email, user_id=user_id)

    @staticmethod
    async def _send_password_reset_email(email: str, reset_token: str):
        """
        Send password reset email (placeholder).
        """
        # TODO: Implement email sending
        logger.info("Password reset email would be sent", email=email, token=reset_token)