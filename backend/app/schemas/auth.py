"""Authentication request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ─── Request Schemas ───────────────────────────────────────

class UserRegister(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="viewer", pattern="^(admin|researcher|viewer)$")


class UserLogin(BaseModel):
    """Schema for user login (used for JSON-body login)."""
    email: EmailStr
    password: str


class TokenRefresh(BaseModel):
    """Schema for token refresh."""
    refresh_token: str


# ─── Response Schemas ──────────────────────────────────────

class TokenResponse(BaseModel):
    """Schema for JWT token pair response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiry in seconds")


class UserResponse(BaseModel):
    """Schema for user profile response."""
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    detail: Optional[str] = None
