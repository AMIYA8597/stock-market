from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=120)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenRefresh(BaseModel):
    refresh_token: str = Field(..., min_length=20)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordConfirm(BaseModel):
    token: str = Field(..., min_length=24)
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_not_too_common(cls, value: str) -> str:
        if value.lower() in {"password", "12345678", "qwerty"}:
            raise ValueError("Password too common")
        return value


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthMessage(BaseModel):
    message: str
