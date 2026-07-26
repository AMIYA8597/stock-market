from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import razorpay  # type: ignore
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_current_user_or_none, get_db, resolve_user_uuid
from app.models.payment import PaymentTransaction, Plan, Subscription, WalletLedger

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/payments", tags=["payments"])

try:
    razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
except Exception:
    logger.exception("razorpay_client_init_failed; falling back to test-mode orders")
    razorpay_client = None


def _resolve_user_id(current_user: dict | None) -> uuid.UUID:
    return resolve_user_uuid(current_user)


@router.get("/plans")
async def get_plans(db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    result = await db.execute(select(Plan).where(Plan.is_active).order_by(Plan.price_inr.asc()))
    plans = result.scalars().all()
    return {
        "items": [
            {
                "id": str(p.id),
                "name": p.name,
                "description": p.description,
                "price_inr": str(p.price_inr),
                "interval": p.interval,
                "features": json.loads(p.features_json),
            }
            for p in plans
        ]
    }


@router.get("/balance")
async def wallet_balance(
    current_user: dict | None = Depends(get_current_user_or_none),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    user_id = _resolve_user_id(current_user)
    result = await db.execute(select(WalletLedger).where(WalletLedger.user_id == user_id))
    rows = result.scalars().all()

    total = sum(
        (row.amount if row.transaction_type == "credit" else -row.amount for row in rows),
        Decimal("0.00"),
    )
    return {"currency": "INR", "wallet_balance": str(total.quantize(Decimal("0.01")))}


class PaymentIntentRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    method: str = Field(default="RAZORPAY", min_length=3, max_length=20)
    description: str = Field(default="Wallet top-up", min_length=1, max_length=120)


@router.post("/intents")
async def create_intent(
    payload: PaymentIntentRequest,
    current_user: dict | None = Depends(get_current_user_or_none),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    user_id = _resolve_user_id(current_user)

    # 1. Create order in Razorpay
    amount_paise = int(payload.amount * 100)
    receipt_id = f"rcpt_{uuid4().hex[:10]}"

    if razorpay_client is None or settings.RAZORPAY_KEY_ID == "rzp_test_replace_me":
        # Test-mode payment gateway for local setup
        order_id = f"order_{uuid4().hex[:14]}"
    else:
        try:
            order = razorpay_client.order.create(
                {
                    "amount": amount_paise,
                    "currency": payload.currency.upper(),
                    "receipt": receipt_id,
                    "notes": {"user_id": str(user_id), "description": payload.description},
                }
            )
            order_id = order["id"]
        except Exception as exc:
            logger.exception("razorpay_order_create_failed: receipt=%s", receipt_id)
            raise HTTPException(
                status_code=502, detail="Payment provider is unavailable. Please retry."
            ) from exc

    # 2. Record transaction intent in DB
    intent_id = f"pi_{uuid4().hex}"
    tx = PaymentTransaction(
        user_id=user_id,
        intent_id=intent_id,
        provider_ref=order_id,
        idempotency_key=uuid4().hex,  # Auto idempotency for this example
        amount=payload.amount,
        currency=payload.currency.upper(),
        method=payload.method,
        status="requires_confirmation",
        metadata_json=json.dumps({"description": payload.description, "receipt": receipt_id}),
    )
    db.add(tx)
    await db.commit()
    await db.refresh(tx)

    return {
        "intent_id": tx.intent_id,
        "provider_ref": tx.provider_ref,
        "amount": str(tx.amount),
        "currency": tx.currency,
        "status": tx.status,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
    }


class PaymentConfirmRequest(BaseModel):
    intent_id: str
    razorpay_payment_id: str
    razorpay_order_id: str | None = None
    razorpay_signature: str | None = None


@router.post("/confirm")
async def confirm_intent(
    payload: PaymentConfirmRequest,
    current_user: dict | None = Depends(get_current_user_or_none),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    _resolve_user_id(current_user)

    result = await db.execute(
        select(PaymentTransaction).where(PaymentTransaction.intent_id == payload.intent_id)
    )
    tx = result.scalar_one_or_none()

    if not tx or (payload.razorpay_order_id and tx.provider_ref != payload.razorpay_order_id):
        raise HTTPException(status_code=404, detail="Payment intent not found or mismatch.")

    if tx.status == "succeeded":
        return {"status": "already_succeeded"}

    if razorpay_client is None or settings.RAZORPAY_KEY_SECRET == "replace_me":
        # Test-mode signature verification for local setup
        pass
    else:
        params_dict = {
            "razorpay_order_id": payload.razorpay_order_id,
            "razorpay_payment_id": payload.razorpay_payment_id,
            "razorpay_signature": payload.razorpay_signature,
        }
        try:
            razorpay_client.utility.verify_payment_signature(params_dict)
        except Exception as e:
            logger.error(f"Razorpay signature verification failed: {e}")
            raise HTTPException(status_code=400, detail="Signature verification failed.") from e

    # Mark transaction as succeeded
    tx.status = "succeeded"
    tx.confirmed_at = datetime.now(UTC)
    tx.provider_event_id = payload.razorpay_payment_id

    # Credit the user's wallet
    ledger = WalletLedger(
        user_id=tx.user_id,
        amount=tx.amount,
        transaction_type="credit",
        description="Wallet top-up via Razorpay",
        reference_id=tx.intent_id,
    )
    db.add(ledger)
    await db.commit()

    return {
        "intent_id": tx.intent_id,
        "status": tx.status,
        "credited_amount": str(tx.amount),
        "completed_at": tx.confirmed_at.isoformat(),
    }


class SubscribeRequest(BaseModel):
    plan_id: str


@router.post("/subscribe")
async def subscribe_to_plan(
    payload: SubscribeRequest,
    current_user: dict | None = Depends(get_current_user_or_none),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    user_id = _resolve_user_id(current_user)

    plan_result = await db.execute(select(Plan).where(Plan.id == payload.plan_id))
    plan = plan_result.scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")

    # Deduct from wallet
    balance_result = await db.execute(select(WalletLedger).where(WalletLedger.user_id == user_id))
    rows = balance_result.scalars().all()
    total = sum(
        (row.amount if row.transaction_type == "credit" else -row.amount for row in rows),
        Decimal("0.00"),
    )

    if total < plan.price_inr:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance.")

    # Debit wallet
    debit = WalletLedger(
        user_id=user_id,
        amount=plan.price_inr,
        transaction_type="debit",
        description=f"Subscription to {plan.name}",
        reference_id=f"sub_{uuid4().hex[:10]}",
    )
    db.add(debit)

    # Create subscription
    sub = Subscription(
        user_id=user_id,
        plan_id=plan.id,
        status="active",
        current_period_end=datetime.now(UTC),  # TODO: add 1 month
    )
    db.add(sub)
    await db.commit()

    return {"status": "subscribed", "plan": plan.name}


@router.get("/history")
async def payment_history(
    limit: int = 20,
    current_user: dict | None = Depends(get_current_user_or_none),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    user_id = _resolve_user_id(current_user)

    # Fetch from WalletLedger instead of PaymentIntent for accurate history
    stmt = (
        select(WalletLedger)
        .where(WalletLedger.user_id == user_id)
        .order_by(WalletLedger.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return {
        "items": [
            {
                "id": str(row.id),
                "amount": str(row.amount),
                "type": row.transaction_type,
                "description": row.description,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ],
        "total": len(rows),
    }


@router.get("/subscription")
async def get_subscription(
    current_user: dict | None = Depends(get_current_user_or_none),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    uid = _resolve_user_id(current_user)

    result = await db.execute(
        select(Subscription, Plan)
        .join(Plan, Subscription.plan_id == Plan.id)
        .where(Subscription.user_id == uid, Subscription.status == "active")
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    row = result.first()
    if not row:
        return {"subscription": None}

    sub, plan = row
    return {
        "subscription": {
            "id": str(sub.id),
            "status": sub.status,
            "current_period_end": sub.current_period_end.isoformat(),
            "plan": {"name": plan.name, "features": json.loads(plan.features_json)},
        }
    }
