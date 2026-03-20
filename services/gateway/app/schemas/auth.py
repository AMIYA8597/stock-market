"""
Pydantic schemas for authentication endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr = Field(..., description="User email address")
    role: str = Field(default="ANALYST", description="User role")


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, description="User password")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    """Schema for user profile updates."""
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """Schema for user response."""
    id: str
    is_active: bool
    email_verified_at: Optional[datetime]
    last_login_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class TokenRefresh(BaseModel):
    """Token refresh request schema."""
    refresh_token: str


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class PasswordResetRequest(BaseModel):
    """Password reset request schema."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation schema."""
    token: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class PasswordChange(BaseModel):
    """Password change schema."""
    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class TOTPSetupResponse(BaseModel):
    """TOTP setup response schema."""
    secret: str
    qr_code_url: str
    backup_codes: list[str]


class TOTPVerify(BaseModel):
    """TOTP verification schema."""
    code: str = Field(..., min_length=6, max_length=6)


class BackupCodeVerify(BaseModel):
    """Backup code verification schema."""
    code: str = Field(..., min_length=10, max_length=10)


class EmailVerificationRequest(BaseModel):
    """Email verification request schema."""
    token: str


class AuthResponse(BaseModel):
    """Generic auth response."""
    success: bool
    message: str
    data: Optional[dict] = None