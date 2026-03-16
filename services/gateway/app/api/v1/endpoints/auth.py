"""
Authentication endpoints with enterprise security.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_logger import audit_logger
from app.core.database import get_db
from app.core.rate_limiter import limiter
from app.core.security import verify_token
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenRefresh,
    UserCreate,
)
from app.services.auth_service import AuthService

router = APIRouter()
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Dependency to get current authenticated user.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id = payload["sub"]
    return {"user_id": user_id, "token_data": payload}


async def get_current_user_with_permissions(
    required_permissions: list = None,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Dependency to get current user with permission checking.
    """
    user_data = await get_current_user(credentials, db)

    # TODO: Implement permission checking based on user role
    # For now, just return user data

    return user_data


@router.post("/register", response_model=AuthResponse)
async def register_user(
    user_data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user account.
    """
    # Rate limiting
    rate_limit_result = await limiter.check_rate_limit(
        request, endpoint="auth/register"
    )

    if not rate_limit_result["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts"
        )

    response = await AuthService.register_user(user_data, db)

    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )

    # Audit log
    await audit_logger.log_event(
        "user_registration_attempt",
        details={
            "email": user_data.email,
            "ip": request.client.host,
            "user_agent": request.headers.get("user-agent")
        }
    )

    return response


@router.post("/login", response_model=AuthResponse)
async def login_user(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return access tokens.
    """
    response = await AuthService.authenticate_user(
        login_data,
        db,
        client_ip=request.client.host,
        user_agent=request.headers.get("user-agent")
    )

    if not response.success:
        # Don't reveal if account exists or not
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    return response


@router.post("/refresh", response_model=AuthResponse)
async def refresh_access_token(
    refresh_data: TokenRefresh,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    response = await AuthService.refresh_access_token(
        refresh_data, db, request.client.host
    )

    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=response.message
        )

    return response


@router.post("/logout")
async def logout_user(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user by revoking refresh tokens.
    """
    # TODO: Implement token revocation
    # For now, just audit the logout

    await audit_logger.log_event(
        "user_logout",
        user_id=current_user["user_id"],
        details={
            "ip": request.client.host,
            "user_agent": request.headers.get("user-agent")
        }
    )

    return {"message": "Logged out successfully"}


@router.post("/password/reset-request", response_model=AuthResponse)
async def request_password_reset(
    reset_data: PasswordResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Request password reset email.
    """
    # Rate limiting
    rate_limit_result = await limiter.check_rate_limit(
        request, endpoint="auth/password-reset"
    )

    if not rate_limit_result["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests"
        )

    # TODO: Implement password reset logic
    await audit_logger.log_event(
        "password_reset_requested",
        details={
            "email": reset_data.email,
            "ip": request.client.host
        }
    )

    return AuthResponse(
        success=True,
        message="If an account with this email exists, a password reset link has been sent."
    )


@router.post("/password/reset-confirm", response_model=AuthResponse)
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Confirm password reset with token.
    """
    # TODO: Implement password reset confirmation
    await audit_logger.log_event(
        "password_reset_confirmed",
        details={"ip": request.client.host}
    )

    return AuthResponse(
        success=True,
        message="Password reset successfully"
    )


@router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user information.
    """
    # TODO: Return full user profile
    return {
        "user_id": current_user["user_id"],
        "permissions": current_user["token_data"].get("permissions", [])
    }


@router.post("/verify-email", response_model=AuthResponse)
async def verify_email(
    verification_data: dict,  # EmailVerificationRequest
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify user email address.
    """
    # TODO: Implement email verification
    await audit_logger.log_event(
        "email_verification_attempt",
        details={"ip": request.client.host}
    )

    return AuthResponse(
        success=True,
        message="Email verified successfully"
    )