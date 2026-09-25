import hashlib
import hmac
import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import RequestContext, get_current_context
from app.database.connection import get_db
from app.models.billing import OrganizationSubscription, PaymentEvent, Plan

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
                "description": p.description,
                "price_inr": str(p.price_inr),
                "billing_period": p.billing_period,
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
    is_test_mode = getattr(settings, "ENVIRONMENT", "production") != "production" or _is_placeholder(secret)

    is_verified = False
    if not _is_placeholder(secret):
        expected_sig = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        is_verified = hmac.compare_digest(expected_sig, signature)
    elif is_test_mode:
        # In test mode with placeholder secret, bypass verification
        is_verified = True

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("Invalid Razorpay webhook payload: %s", type(exc).__name__)
        raise HTTPException(status_code=400, detail="Invalid webhook payload") from exc

    event_type = payload.get("event", "unknown")
    provider_event_id = payload.get("id", str(uuid.uuid4()))
    logger.info(f"Billing webhook received: event={event_type}, verified={is_verified}")

    # 2. Log to Audit Table (regardless of verification)
    audit = PaymentEvent(
        provider="razorpay",
        provider_event_id=provider_event_id,
        event_type=event_type,
        payload=payload,
        processing_status="pending" if is_verified else "failed",
        error_message=None if is_verified else "Invalid webhook signature"
    )
    db.add(audit)

    if not is_verified:
        await db.commit()
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

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
            audit.processed_at = datetime.now(UTC)
        else:
            audit.processing_status = "ignored"
            audit.error_message = f"Subscription {sub_id} not found"

    await db.commit()
    return {"status": "ok"}

class IntentPayload(BaseModel):
    plan_id: str
    method: str
    currency: str = "INR"
    description: str | None = None


class ConfirmPayload(BaseModel):
    intent_id: str
    razorpay_payment_id: str
    razorpay_signature: str | None = None


@router.post("/intents")
async def create_intent(
    payload: IntentPayload,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    """Create a payment intent for a subscription plan.

    Unlike the previous implementation, this never fabricates a fake
    "created" response: it either creates a real Razorpay order (when real
    provider credentials are configured) or, in test/dev mode, records an
    honestly-labeled test intent that /confirm can only complete against.
    """
    if not ctx.organization_id:
        raise HTTPException(status_code=403, detail="Organization context required")

    try:
        plan_uuid = uuid.UUID(payload.plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid plan_id") from exc

    plan_result = await db.execute(select(Plan).where(Plan.id == plan_uuid, Plan.is_active))
    plan = plan_result.scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found or inactive")

    key_id = getattr(settings, "RAZORPAY_KEY_ID", "")
    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
    is_test_mode = (
        getattr(settings, "ENVIRONMENT", "production") != "production"
        or _is_placeholder(key_id)
        or _is_placeholder(key_secret)
    )

    intent_id = f"pi_{uuid.uuid4().hex[:16]}"
    # Amount always comes from the server-side Plan record, never the client,
    # so a caller cannot pay less than the real plan price.
    amount_paise = int(round(float(plan.price_inr) * 100))

    provider_order_id: str
    if is_test_mode:
        provider_order_id = f"test_order_{uuid.uuid4().hex[:16]}"
    else:
        # Real Razorpay Orders API call. Any failure here is surfaced as a
        # 503, never as a fabricated "created" response.
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://api.razorpay.com/v1/orders",
                    auth=(key_id, key_secret),
                    json={
                        "amount": amount_paise,
                        "currency": payload.currency,
                        "receipt": intent_id,
                        "notes": {"plan_id": payload.plan_id, "organization_id": ctx.organization_id},
                    },
                )
                resp.raise_for_status()
                provider_order_id = resp.json()["id"]
        except Exception as exc:
            logger.error(f"Razorpay order creation failed: {exc}")
            raise HTTPException(
                status_code=503, detail="Payment provider unavailable; could not create order."
            ) from exc

    audit = PaymentEvent(
        provider="razorpay",
        provider_event_id=intent_id,
        event_type="intent.created",
        payload={
            "plan_id": payload.plan_id,
            "organization_id": ctx.organization_id,
            "provider_order_id": provider_order_id,
            "currency": payload.currency,
        },
        processing_status="test_mode" if is_test_mode else "pending",
    )
    db.add(audit)
    await db.commit()

    return {
        "intent_id": intent_id,
        "provider_order_id": provider_order_id,
        "status": "created",
        "is_test_mode": is_test_mode,
    }


@router.post("/confirm")
async def confirm_intent(
    payload: ConfirmPayload,
    ctx: RequestContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    """Confirm a previously-created intent.

    Never reports success for an intent that was never created, and never
    skips signature verification outside the same explicit test-mode used
    by the webhook handler above.
    """
    event_result = await db.execute(
        select(PaymentEvent).where(
            PaymentEvent.provider_event_id == payload.intent_id,
            PaymentEvent.event_type == "intent.created",
        )
    )
    intent = event_result.scalar_one_or_none()
    if intent is None:
        raise HTTPException(status_code=404, detail="Unknown or expired intent_id")
    if intent.processing_status not in ("pending", "test_mode"):
        raise HTTPException(status_code=409, detail=f"Intent already {intent.processing_status}")

    key_secret = getattr(settings, "RAZORPAY_KEY_SECRET", "")
    provider_order_id = intent.payload.get("provider_order_id", "")

    if intent.processing_status == "pending":
        # Real Razorpay checkout signature: HMAC-SHA256(order_id|payment_id, key_secret)
        if not payload.razorpay_signature or _is_placeholder(key_secret):
            intent.processing_status = "failed"
            intent.error_message = "Missing signature or provider not configured"
            await db.commit()
            raise HTTPException(status_code=400, detail="Payment signature verification failed")

        expected_sig = hmac.new(
            key_secret.encode(),
            f"{provider_order_id}|{payload.razorpay_payment_id}".encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_sig, payload.razorpay_signature):
            intent.processing_status = "failed"
            intent.error_message = "Signature mismatch"
            await db.commit()
            raise HTTPException(status_code=400, detail="Payment signature verification failed")

    intent.processing_status = "processed"
    intent.processed_at = datetime.now(UTC)
    intent.payload = {**intent.payload, "razorpay_payment_id": payload.razorpay_payment_id}

    plan_id = intent.payload.get("plan_id")
    if plan_id and ctx.organization_id:
        org_id = uuid.UUID(ctx.organization_id)
        sub_result = await db.execute(
            select(OrganizationSubscription).where(
                OrganizationSubscription.organization_id == org_id
            )
        )
        sub = sub_result.scalar_one_or_none()
        if sub is None:
            sub = OrganizationSubscription(
                organization_id=org_id,
                plan_id=uuid.UUID(plan_id),
                status="active",
                provider="razorpay",
                provider_subscription_id=provider_order_id or None,
            )
            db.add(sub)
        else:
            sub.plan_id = uuid.UUID(plan_id)
            sub.status = "active"

    await db.commit()

    return {
        "intent_id": payload.intent_id,
        "status": "success",
        "completed_at": intent.processed_at.isoformat(),
    }
