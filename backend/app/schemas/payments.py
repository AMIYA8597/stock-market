"""Payments and wallet funding schemas (Pydantic v2)."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class PaymentMethod(BaseModel):
    code: str = Field(..., description="UPI|CARD|NETBANKING")
    label: str
    enabled: bool = True
    min_amount: Decimal = Field(..., gt=0, decimal_places=2)
    max_amount: Decimal = Field(..., gt=0, decimal_places=2)


class PaymentMethodsResponse(BaseModel):
    methods: list[PaymentMethod]
    generated_at: datetime


class PaymentIntentRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    method: str = Field(..., description="UPI|CARD|NETBANKING")
    description: str = Field(default="Wallet top-up", min_length=1, max_length=120)


class PaymentIntentResponse(BaseModel):
    intent_id: str
    provider_ref: str
    amount: Decimal = Field(..., decimal_places=2)
    currency: str
    method: str
    status: str = Field(..., description="requires_confirmation|confirmed|failed")
    created_at: datetime


class PaymentConfirmRequest(BaseModel):
    intent_id: str
    confirmation_code: str = Field(default="000000", min_length=4, max_length=16)


class PaymentConfirmResponse(BaseModel):
    payment_id: str
    intent_id: str
    status: str = Field(..., description="succeeded|failed")
    credited_amount: Decimal = Field(..., decimal_places=2)
    wallet_balance: Decimal = Field(..., decimal_places=2)
    completed_at: datetime


class WalletBalanceResponse(BaseModel):
    currency: str
    wallet_balance: Decimal = Field(..., decimal_places=2)
    updated_at: datetime


class PaymentHistoryItem(BaseModel):
    payment_id: str
    intent_id: str
    amount: Decimal = Field(..., decimal_places=2)
    currency: str
    method: str
    status: str
    created_at: datetime
    completed_at: datetime | None = None


class PaymentHistoryResponse(BaseModel):
    items: list[PaymentHistoryItem]
    total: int
    limit: int
