"""Pydantic schemas for trade journal endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class JournalCreate(BaseModel):
    """Schema for creating a trade journal entry."""

    symbol: str = Field(..., min_length=1, max_length=32, description="Ticker symbol or instrument")
    notes: str = Field(..., max_length=1024, description="Trade analysis or notes")
    tags: Optional[str] = Field(default=None, max_length=255, description="Comma-separated strategy tags")
    rating: Optional[int] = Field(default=None, ge=1, le=5, description="Star rating (1 to 5)")
    entry_price: Optional[Decimal] = Field(default=None, ge=0, decimal_places=8)
    exit_price: Optional[Decimal] = Field(default=None, ge=0, decimal_places=8)
    quantity: Optional[Decimal] = Field(default=None, ge=0, decimal_places=8)
    direction: Optional[str] = Field(default=None, max_length=8, description="LONG or SHORT")


class JournalUpdate(BaseModel):
    """Schema for updating a trade journal entry."""

    symbol: Optional[str] = Field(default=None, min_length=1, max_length=32)
    notes: Optional[str] = Field(default=None, max_length=1024)
    tags: Optional[str] = Field(default=None, max_length=255)
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    entry_price: Optional[Decimal] = Field(default=None, ge=0, decimal_places=8)
    exit_price: Optional[Decimal] = Field(default=None, ge=0, decimal_places=8)
    quantity: Optional[Decimal] = Field(default=None, ge=0, decimal_places=8)
    direction: Optional[str] = Field(default=None, max_length=8)


class JournalResponse(BaseModel):
    """Response schema for trade journal entries."""

    id: UUID
    user_id: UUID
    symbol: str
    notes: str
    tags: Optional[str] = None
    rating: Optional[int] = None
    entry_price: Optional[Decimal] = None
    exit_price: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    direction: Optional[str] = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
