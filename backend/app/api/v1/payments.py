"""Payment and wallet top-up endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_or_none, get_db
from app.schemas.payments import (
    PaymentConfirmRequest,
    PaymentConfirmResponse,
    PaymentHistoryItem,
    PaymentHistoryResponse,
    PaymentIntentRequest,
    PaymentIntentResponse,
    PaymentMethodsResponse,
    PaymentMethod,
    WalletBalanceResponse,
)

router = APIRouter(tags=["payments"])

# In-memory demo store; replace with persistent table in production DB migration.
_WALLET_BY_USER: dict[str, Decimal] = {}
_INTENTS: dict[str, dict] = {}
_PAYMENTS: list[PaymentHistoryItem] = []

_ALLOWED_METHODS = {
    "UPI": (Decimal("100.00"), Decimal("200000.00")),
    "CARD": (Decimal("100.00"), Decimal("500000.00")),
    "NETBANKING": (Decimal("500.00"), Decimal("1000000.00")),
}


def _resolve_user_id(current_user: dict | None) -> str:
    if not current_user:
        return "demo-user"
    user_id = current_user.get("user_id") or current_user.get("sub")
    return str(user_id) if user_id else "demo-user"


@router.get("/methods", response_model=PaymentMethodsResponse, summary="Available payment methods")
async def get_methods() -> PaymentMethodsResponse:
    methods = [
        PaymentMethod(
            code=code,
            label=code.replace("NETBANKING", "Net Banking"),
            enabled=True,
            min_amount=bounds[0],
            max_amount=bounds[1],
        )
        for code, bounds in _ALLOWED_METHODS.items()
    ]
    return PaymentMethodsResponse(methods=methods, generated_at=datetime.now(timezone.utc))


@router.get("/balance", response_model=WalletBalanceResponse, summary="Wallet cash balance")
async def get_balance(
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_or_none),
) -> WalletBalanceResponse:
    _ = db
    user_id = _resolve_user_id(current_user)
    balance = _WALLET_BY_USER.get(user_id, Decimal("0.00"))
    return WalletBalanceResponse(currency="INR", wallet_balance=balance, updated_at=datetime.now(timezone.utc))


@router.post("/intents", response_model=PaymentIntentResponse, summary="Create payment intent")
async def create_intent(
    request: PaymentIntentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_or_none),
) -> PaymentIntentResponse:
    _ = db
    _ = current_user

    method = request.method.upper()
    if method not in _ALLOWED_METHODS:
        raise HTTPException(status_code=400, detail="unsupported payment method")

    min_amount, max_amount = _ALLOWED_METHODS[method]
    if request.amount < min_amount or request.amount > max_amount:
        raise HTTPException(
            status_code=400,
            detail=f"amount must be between {min_amount} and {max_amount} for {method}",
        )

    intent_id = f"pi_{uuid4().hex}"
    provider_ref = f"gw_{uuid4().hex[:16]}"
    now = datetime.now(timezone.utc)

    _INTENTS[intent_id] = {
        "intent_id": intent_id,
        "provider_ref": provider_ref,
        "amount": request.amount.quantize(Decimal("0.01")),
        "currency": request.currency.upper(),
        "method": method,
        "status": "requires_confirmation",
        "created_at": now,
    }

    return PaymentIntentResponse(**_INTENTS[intent_id])


@router.post("/confirm", response_model=PaymentConfirmResponse, summary="Confirm payment intent")
async def confirm_intent(
    request: PaymentConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_or_none),
) -> PaymentConfirmResponse:
    _ = db
    user_id = _resolve_user_id(current_user)

    intent = _INTENTS.get(request.intent_id)
    if intent is None:
        raise HTTPException(status_code=404, detail="payment intent not found")

    if intent["status"] == "confirmed":
        existing = next((p for p in _PAYMENTS if p.intent_id == request.intent_id), None)
        if existing is None:
            raise HTTPException(status_code=409, detail="payment already confirmed but payment record missing")
        return PaymentConfirmResponse(
            payment_id=existing.payment_id,
            intent_id=existing.intent_id,
            status="succeeded",
            credited_amount=existing.amount,
            wallet_balance=_WALLET_BY_USER.get(user_id, Decimal("0.00")),
            completed_at=existing.completed_at or datetime.now(timezone.utc),
        )

    if request.confirmation_code.strip() == "":
        raise HTTPException(status_code=400, detail="confirmation_code is required")

    intent["status"] = "confirmed"
    completed_at = datetime.now(timezone.utc)
    amount = Decimal(intent["amount"]).quantize(Decimal("0.01"))

    current_balance = _WALLET_BY_USER.get(user_id, Decimal("0.00"))
    new_balance = (current_balance + amount).quantize(Decimal("0.01"))
    _WALLET_BY_USER[user_id] = new_balance

    payment = PaymentHistoryItem(
        payment_id=f"pay_{uuid4().hex}",
        intent_id=request.intent_id,
        amount=amount,
        currency=intent["currency"],
        method=intent["method"],
        status="succeeded",
        created_at=intent["created_at"],
        completed_at=completed_at,
    )
    _PAYMENTS.insert(0, payment)

    return PaymentConfirmResponse(
        payment_id=payment.payment_id,
        intent_id=payment.intent_id,
        status="succeeded",
        credited_amount=amount,
        wallet_balance=new_balance,
        completed_at=completed_at,
    )


@router.get("/history", response_model=PaymentHistoryResponse, summary="Payment transaction history")
async def get_history(
    limit: int = Query(default=20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_or_none),
) -> PaymentHistoryResponse:
    _ = db
    _ = current_user
    items = _PAYMENTS[:limit]
    return PaymentHistoryResponse(items=items, total=len(_PAYMENTS), limit=limit)
