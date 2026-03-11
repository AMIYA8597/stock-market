<<<<<<< HEAD
"""Authentication request/response schemas with 2FA and security features."""
=======
"""Authentication request/response schemas."""
>>>>>>> 10e1aa79ae3f95f38345cbdf853c86957900630c

from __future__ import annotations

from datetime import datetime
from typing import Optional

<<<<<<< HEAD
from pydantic import BaseModel, EmailStr, Field, field_validator
=======
from pydantic import BaseModel, EmailStr, Field
>>>>>>> 10e1aa79ae3f95f38345cbdf853c86957900630c


# ─── Request Schemas ───────────────────────────────────────

class UserRegister(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
<<<<<<< HEAD

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        # Check against common weak passwords (basic check)
        if v.lower() in ['password', '123456', 'qwerty']:
            raise ValueError('Password too common')
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str
    totp_code: Optional[str] = Field(None, description="TOTP code if 2FA enabled")
    backup_code: Optional[str] = Field(None, description="Backup code if TOTP unavailable")
=======
    full_name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="viewer", pattern="^(admin|researcher|viewer)$")


class UserLogin(BaseModel):
    """Schema for user login (used for JSON-body login)."""
    email: EmailStr
    password: str
>>>>>>> 10e1aa79ae3f95f38345cbdf853c86957900630c


class TokenRefresh(BaseModel):
    """Schema for token refresh."""
    refresh_token: str


<<<<<<< HEAD
class Enable2FA(BaseModel):
    """Schema for enabling 2FA."""
    password: str  # Verify current password
    totp_code: str  # Verify TOTP setup


class Verify2FA(BaseModel):
    """Schema for verifying 2FA setup."""
    totp_code: str


class Disable2FA(BaseModel):
    """Schema for disabling 2FA."""
    password: str
    backup_codes: list[str] = Field(..., min_items=10, max_items=10)  # Require all backup codes


class ChangePassword(BaseModel):
    """Schema for password change."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if v.lower() in ['password', '123456', 'qwerty']:
            raise ValueError('Password too common')
        return v


class ResetPasswordRequest(BaseModel):
    """Schema for password reset request."""
    email: EmailStr


class ResetPasswordConfirm(BaseModel):
    """Schema for password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


=======
>>>>>>> 10e1aa79ae3f95f38345cbdf853c86957900630c
# ─── Response Schemas ──────────────────────────────────────

class TokenResponse(BaseModel):
    """Schema for JWT token pair response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
<<<<<<< HEAD
    expires_in: int = Field(900, description="Access token expiry in seconds (15 min)")
=======
    expires_in: int = Field(..., description="Access token expiry in seconds")
>>>>>>> 10e1aa79ae3f95f38345cbdf853c86957900630c


class UserResponse(BaseModel):
    """Schema for user profile response."""
<<<<<<< HEAD
    id: str
    email: str  # Decrypted for display
    role: str
    is_active: bool
    is_2fa_enabled: bool
    email_verified_at: Optional[datetime]
    last_login_at: Optional[datetime]
=======
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
>>>>>>> 10e1aa79ae3f95f38345cbdf853c86957900630c
    created_at: datetime

    model_config = {"from_attributes": True}


<<<<<<< HEAD
class TOTPSetupResponse(BaseModel):
    """Schema for TOTP setup response."""
    secret: str
    uri: str
    qr_code_url: str


class BackupCodesResponse(BaseModel):
    """Schema for backup codes response."""
    backup_codes: list[str]


=======
>>>>>>> 10e1aa79ae3f95f38345cbdf853c86957900630c
class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    detail: Optional[str] = None
