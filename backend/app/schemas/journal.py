"""Pydantic schemas for trade journal endpoints."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class JournalCreate(BaseModel):
    """Schema for creating a trade journal entry."""

    symbol: str = Field(..., min_length=1, max_length=32, description="Ticker symbol or instrument")
    notes: str = Field(..., max_length=1024, description="Trade analysis or notes")
    tags: str | None = Field(default=None, max_length=255, description="Comma-separated strategy tags")
    rating: int | None = Field(default=None, ge=1, le=5, description="Star rating (1 to 5)")
    entry_price: Decimal | None = Field(default=None, ge=0)
    exit_price: Decimal | None = Field(default=None, ge=0)
    quantity: Decimal | None = Field(default=None, ge=0)
    direction: str | None = Field(default=None, max_length=8, description="LONG or SHORT")


class JournalUpdate(BaseModel):
    """Schema for updating a trade journal entry."""

    symbol: str | None = Field(default=None, min_length=1, max_length=32)
    notes: str | None = Field(default=None, max_length=1024)
    tags: str | None = Field(default=None, max_length=255)
    rating: int | None = Field(default=None, ge=1, le=5)
    entry_price: Decimal | None = Field(default=None, ge=0)
    exit_price: Decimal | None = Field(default=None, ge=0)
    quantity: Decimal | None = Field(default=None, ge=0)
    direction: str | None = Field(default=None, max_length=8)


class JournalResponse(BaseModel):
    """Response schema for trade journal entries."""

    id: UUID
    user_id: UUID
    symbol: str
    notes: str
    tags: str | None = None
    rating: int | None = None
    entry_price: Decimal | None = None
    exit_price: Decimal | None = None
    quantity: Decimal | None = None
    direction: str | None = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
