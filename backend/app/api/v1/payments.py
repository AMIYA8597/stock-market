import logging
import json
import hashlib
import hmac
from datetime import datetime, timezone
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import get_current_context, RequestContext
from app.database.connection import get_db
from app.models.billing import Plan, OrganizationSubscription, PaymentEvent

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/payments", tags=["payments"])

def _is_placeholder(value: str | None) -> bool:
    if not value:
        return True
    return "replace_me" in value.lower()

class SubscriptionResponse(BaseModel):
    id: str
    status: str
    plan_name: str
    current_period_end: str | None

@router.get("/plans")
async def get_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plan).where(Plan.is_active))
    plans = result.scalars().all()
    return {
        "items": [
            {
                "id": str(p.id),
                "name": p.name,
                "description": p.description
            }
            for p in plans
        ]
    }

@router.get("/subscription", response_model=SubscriptionResponse | None)
async def get_subscription(
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db)
):
    if not ctx.organization_id:
        raise HTTPException(status_code=403, detail="Organization context required")
        
    org_id = uuid.UUID(ctx.organization_id)
    result = await db.execute(
        select(OrganizationSubscription, Plan)
        .join(Plan, OrganizationSubscription.plan_id == Plan.id)
        .where(OrganizationSubscription.organization_id == org_id, OrganizationSubscription.status == "active")
        .order_by(OrganizationSubscription.created_at.desc())
        .limit(1)
    )
    row = result.first()
    if not row:
        return None
        
    sub, plan = row
    return SubscriptionResponse(
        id=str(sub.id),
        status=sub.status,
        plan_name=plan.name,
        current_period_end=sub.current_period_end.isoformat() if sub.current_period_end else None
    )

@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    raw_body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")

    secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "REPLACE_ME")
    if _is_placeholder(secret):
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
        
    expected_sig = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    is_verified = hmac.compare_digest(expected_sig, signature)

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("Invalid Razorpay webhook payload: %s", type(exc).__name__)
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from exc

    event_type = payload.get("event", "unknown")
    provider_event_id = payload.get("id", str(uuid.uuid4()))
    
    if not is_verified:
        logger.warning(f"Invalid webhook signature for event={event_type}")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    
    # Idempotency check
    existing = await db.execute(select(PaymentEvent).where(PaymentEvent.provider_event_id == provider_event_id))
    if existing.scalar_one_or_none():
        logger.info(f"Billing webhook idempotency hit: event={event_type}, id={provider_event_id}")
        return {"status": "ok", "message": "Already processed"}
        
    logger.info(f"Billing webhook received: event={event_type}, verified={is_verified}")
    
    # 2. Log to Audit Table
    audit = PaymentEvent(
        provider="razorpay",
        provider_event_id=provider_event_id,
        event_type=event_type,
        payload=payload,
        processing_status="pending",
        error_message=None
    )
    db.add(audit)

    # 3. Process events
    sub_id = payload.get("payload", {}).get("subscription", {}).get("entity", {}).get("id")

    if sub_id and event_type in [
        "subscription.activated",
        "subscription.charged",
        "subscription.cancelled",
        "subscription.halted",
    ]:
        sub_result = await db.execute(
            select(OrganizationSubscription).where(OrganizationSubscription.provider_subscription_id == sub_id)
        )
        sub = sub_result.scalar_one_or_none()
        if sub:
            if event_type in ["subscription.activated", "subscription.charged"]:
                sub.status = "active"
            elif event_type in ["subscription.cancelled", "subscription.halted"]:
                sub.status = "cancelled"
            audit.processing_status = "processed"
            audit.processed_at = datetime.now(timezone.utc)
        else:
            audit.processing_status = "ignored"
            audit.error_message = f"Subscription {sub_id} not found"

    await db.commit()
    return {"status": "ok"}


import razorpay

def get_razorpay_client():
    if _is_placeholder(settings.RAZORPAY_KEY_ID) or _is_placeholder(settings.RAZORPAY_KEY_SECRET):
        raise HTTPException(status_code=500, detail="Razorpay not configured")
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class IntentPayload(BaseModel):
    amount: float
    method: str
    currency: str = "INR"
    description: str | None = None

@router.post("/intents")
async def create_intent(payload: IntentPayload):
    client = get_razorpay_client()
    # Amount in paise
    amount_in_paise = int(payload.amount * 100)
    data = {
        "amount": amount_in_paise,
        "currency": payload.currency,
        "receipt": f"receipt_{uuid.uuid4().hex[:10]}",
        "notes": {
            "description": payload.description or ""
        }
    }
    
    try:
        order = client.order.create(data=data)
        return {
            "intent_id": order["id"],
            "provider_ref": order["receipt"],
            "amount": str(payload.amount),
            "status": "created"
        }
    except Exception as e:
        logger.error(f"Razorpay order creation failed: {e}")
        raise HTTPException(status_code=500, detail="Payment provider error")

class ConfirmPayload(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

@router.post("/confirm")
async def confirm_intent(payload: ConfirmPayload):
    client = get_razorpay_client()
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': payload.razorpay_order_id,
            'razorpay_payment_id': payload.razorpay_payment_id,
            'razorpay_signature': payload.razorpay_signature
        })
        
        # We should ideally fetch the payment and ensure it's captured
        payment = client.payment.fetch(payload.razorpay_payment_id)
        credited_amount = payment.get('amount', 0) / 100.0
        
        return {
            "intent_id": payload.razorpay_order_id,
            "status": "success",
            "credited_amount": str(credited_amount),
            "completed_at": datetime.now(timezone.utc).isoformat()
        }
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    except Exception as e:
        logger.error(f"Razorpay confirm failed: {e}")
        raise HTTPException(status_code=500, detail="Payment provider error")
