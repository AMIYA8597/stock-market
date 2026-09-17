import asyncio
import json
import hmac
import hashlib
from datetime import datetime, UTC
from uuid import uuid4

from app.database.connection import async_session_factory
from app.models.user import User
from app.models.payment import Subscription, Plan, BillingAuditLog
from app.core.config import get_settings
from sqlalchemy import select

settings = get_settings()

async def run_test():
    async with async_session_factory() as db:
        # 1. Create a fake user and plan
        user = User(
            email=f"test_billing_{uuid4().hex[:6]}@example.com",
            password_hash="fake",
            full_name="Billing Test User"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        plan = Plan(
            name="Test Pro Plan",
            description="Test plan",
            price_inr=999.0,
            interval="monthly",
            features_json="[]"
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)

        # 2. Create a pending subscription
        rzp_sub_id = f"sub_test_{uuid4().hex[:10]}"
        sub = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            status="created",
            razorpay_subscription_id=rzp_sub_id,
            current_period_end=datetime.now(UTC)
        )
        db.add(sub)
        await db.commit()

        print(f"[*] Created Subscription {sub.id} with status: {sub.status}")

        # 3. Fire the webhook via FastAPI TestClient
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)

        payload = {
            "event": "subscription.charged",
            "payload": {
                "subscription": {
                    "entity": {
                        "id": rzp_sub_id,
                        "current_end": int(datetime.now(UTC).timestamp()) + 30 * 86400
                    }
                }
            }
        }

        payload_bytes = json.dumps(payload).encode("utf-8")

        # Sign it
        secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "replace_me")
        signature = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()

        print("[*] Firing webhook POST /api/v1/payments/webhook")
        response = client.post(
            "/api/v1/payments/webhook",
            content=payload_bytes,
            headers={"x-razorpay-signature": signature, "Content-Type": "application/json"}
        )

        print(f"[*] Webhook Response: {response.status_code} {response.json()}")

        # 4. Direct DB check
        await db.commit() # Clear transaction state to read fresh data from DB
        sub_check = await db.execute(select(Subscription).where(Subscription.razorpay_subscription_id == rzp_sub_id))
        sub_updated = sub_check.scalar_one()

        audit_check = await db.execute(select(BillingAuditLog).where(BillingAuditLog.event_type == "subscription.charged").order_by(BillingAuditLog.created_at.desc()))
        audit_log = audit_check.scalars().first()

        print("\n--- VERIFICATION DB RESULTS ---")
        print(f"Subscription ID: {sub_updated.id}")
        print(f"Razorpay Sub ID: {sub_updated.razorpay_subscription_id}")
        print(f"New Status: {sub_updated.status} (Expected: active)")
        print(f"Current Period End: {sub_updated.current_period_end}")
        print(f"Audit Log Recorded: {audit_log is not None}")
        if audit_log:
            print(f"Audit Log Verified: {audit_log.signature_verified}")

if __name__ == "__main__":
    asyncio.run(run_test())
