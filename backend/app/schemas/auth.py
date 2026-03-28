"""Authentication request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ─── Request Schemas ───────────────────────────────────────

class UserRegister(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if v.lower() in ['password', '123456', 'qwerty']:
            raise ValueError('Password too common')
        return v


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str
    totp_code: Optional[str] = Field(None, description="TOTP code if 2FA enabled")
    backup_code: Optional[str] = Field(None, description="Backup code if TOTP unavailable")


class TokenRefresh(BaseModel):
    """Schema for refresh token requests."""

    refresh_token: str


class Enable2FA(BaseModel):
    """Schema for enabling 2FA."""

    password: str


class Verify2FA(BaseModel):
    """Schema for verifying 2FA setup."""

    totp_code: str


class Disable2FA(BaseModel):
    """Schema for disabling 2FA."""

    password: str
    backup_codes: list[str] = Field(..., min_length=10, max_length=10)


class ChangePassword(BaseModel):
    """Schema for password changes."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if v.lower() in ['password', '123456', 'qwerty']:
            raise ValueError('Password too common')
        return v


class ResetPasswordRequest(BaseModel):
    """Schema for requesting password reset."""

    email: EmailStr


class ResetPasswordConfirm(BaseModel):
    """Schema for confirming password reset."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


# ─── Response Schemas ──────────────────────────────────────

class TokenResponse(BaseModel):
    """Schema for JWT token pair response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(900, description="Access token expiry in seconds (15 min)")


class UserResponse(BaseModel):
    """Schema for user profile response."""

    id: str
    email: str
    role: str
    is_active: bool
    is_2fa_enabled: bool
    email_verified_at: Optional[datetime]
    last_login_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class TOTPSetupResponse(BaseModel):
    """Schema for TOTP setup response."""

    secret: str
    uri: str
    qr_code_url: str


class BackupCodesResponse(BaseModel):
    """Schema for backup codes response."""

    backup_codes: list[str]


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    detail: Optional[str] = None
