import asyncio
import json

from sqlalchemy import select

from app.database.connection import async_session_factory
from app.models.payment import BillingAuditLog, Subscription


async def check():
    async with async_session_factory() as db:
        # get the latest subscription
        res = await db.execute(select(Subscription).order_by(Subscription.created_at.desc()).limit(1))
        sub = res.scalar_one_or_none()

        # get the latest audit log
        res2 = await db.execute(select(BillingAuditLog).order_by(BillingAuditLog.created_at.desc()).limit(1))
        audit = res2.scalar_one_or_none()

        print(f"Latest Sub Status: {sub.status if sub else 'None'}")
        print(f"Latest Sub Rzp ID: {sub.razorpay_subscription_id if sub else 'None'}")
        print(f"Latest Sub Period End: {sub.current_period_end if sub else 'None'}")

        if audit:
            payload = json.loads(audit.payload_json)
            rzp_id_in_payload = payload.get("payload", {}).get("subscription", {}).get("entity", {}).get("id")
            print(f"Audit Payload Event: {audit.event_type}")
            print(f"Audit Payload Rzp ID: {rzp_id_in_payload}")
            print(f"Matches Sub? {sub.razorpay_subscription_id == rzp_id_in_payload}")

if __name__ == "__main__":
    asyncio.run(check())
