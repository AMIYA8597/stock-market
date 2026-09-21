from __future__ import annotations

import json
import logging
import uuid
from decimal import Decimal

import razorpay  # type: ignore
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_current_user, get_db
from app.models.payment import BillingAuditLog, Plan, Subscription, WalletLedger

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/payments", tags=["payments"])

try:
    razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
except Exception:
    razorpay_client = None


def _is_placeholder(value: str | None) -> bool:
    """True if a Razorpay credential is still the unfilled placeholder.

    Was previously an exact case-sensitive match against one specific
    casing ("rzp_test_replace_me"/"replace_me"), while the actual .env
    placeholder is "rzp_test_REPLACE_ME"/"REPLACE_ME" — the mismatch meant
    the placeholder was never detected, so the app always attempted a real
    Razorpay API call with fake credentials instead of using test mode.
    """
    if not value:
        return True
    return "replace_me" in value.lower()


def _resolve_user_id(current_user: dict | None) -> uuid.UUID:
    # get_current_user returns the real User model, not a JWT payload
    # dict — current_user["sub"] here previously always raised TypeError
    # (SQLAlchemy models aren't subscriptable), so every payments endpoint
    # failed with a misleading "Invalid User ID" 401 regardless of auth state.
    if not current_user or not current_user.id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return current_user.id


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
    current_user: dict | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    raise HTTPException(status_code=410, detail="Legacy wallet billing is retired")


class PaymentIntentRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    method: str = Field(default="RAZORPAY", min_length=3, max_length=20)
    description: str = Field(default="Wallet top-up", min_length=1, max_length=120)


@router.post("/intents")
async def create_intent(
    payload: PaymentIntentRequest,
    current_user: dict | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    raise HTTPException(status_code=410, detail="Legacy wallet billing is retired")


class PaymentConfirmRequest(BaseModel):
    intent_id: str
    razorpay_payment_id: str
    razorpay_order_id: str | None = None
    razorpay_signature: str | None = None


@router.post("/confirm")
async def confirm_intent(
    payload: PaymentConfirmRequest,
    current_user: dict | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    raise HTTPException(status_code=410, detail="Legacy wallet billing is retired")


class SubscribeRequest(BaseModel):
    plan_id: str


@router.post("/subscribe")
async def subscribe_to_plan(
    payload: SubscribeRequest,
    current_user: dict | None = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    raise HTTPException(status_code=410, detail="Legacy wallet billing is retired")


@router.get("/history")
async def payment_history(
    limit: int = 20,
    current_user: dict | None = Depends(get_current_user),
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
    current_user: dict | None = Depends(get_current_user),
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


@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    raw_body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")

    # 1. Verify Signature
    import hashlib
    import hmac


    is_verified = False
    secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "REPLACE_ME")
    if not _is_placeholder(secret):
        expected_sig = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        is_verified = hmac.compare_digest(expected_sig, signature)
    else:
        is_verified = False

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("Invalid Razorpay webhook payload: %s", type(exc).__name__)
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from exc

    # 2. Log to Audit Table (regardless of verification)
    event_type = payload.get("event", "unknown")
    logger.info(f"Billing webhook received: event={event_type}, verified={is_verified}")
    audit = BillingAuditLog(
        event_type=event_type,
        payload_json=raw_body.decode("utf-8")[:3999],
        signature_verified=is_verified,
    )
    db.add(audit)

    if not is_verified:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    # 3. Process events (Respond fast without blocking)
    event = payload.get("event")
    payload_entity = payload.get("payload", {}).get("subscription", {}).get("entity", {})
    sub_id = payload_entity.get("id")

    if sub_id and event in [
        "subscription.activated",
        "subscription.charged",
        "subscription.cancelled",
        "subscription.halted",
    ]:
        sub_result = await db.execute(
            select(Subscription).where(Subscription.razorpay_subscription_id == sub_id)
        )
        sub = sub_result.scalar_one_or_none()
        if sub:
            if event == "subscription.activated" or event == "subscription.charged":
                sub.status = "ACTIVE"
            elif event == "subscription.cancelled" or event == "subscription.halted":
                sub.status = "CANCELLED"

    await db.commit()
    return {"status": "ok"}
