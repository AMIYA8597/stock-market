import sys

path = 'app/api/v1/payments.py'

webhook_code = """
@router.post("/webhook")
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    raw_body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")

    # 1. Verify Signature
    from app.core.security import is_test_mode
    import hmac
    import hashlib
    is_verified = False
    secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "replace_me")
    if secret and secret != "replace_me":
        expected_sig = hmac.new(
            secret.encode(),
            raw_body,
            hashlib.sha256
        ).hexdigest()
        is_verified = hmac.compare_digest(expected_sig, signature)
    elif is_test_mode():
        is_verified = True
    else:
        is_verified = False

    payload = json.loads(raw_body.decode("utf-8"))

    # 2. Log to Audit Table (regardless of verification)
    audit = BillingAuditLog(
        event_type=payload.get("event", "unknown"),
        payload_json=raw_body.decode("utf-8")[:3999],
        signature_verified=is_verified
    )
    db.add(audit)

    if not is_verified:
        await db.commit()
        return {"status": "logged_unverified"}

    # 3. Process events (Respond fast without blocking)
    event = payload.get("event")
    payload_entity = payload.get("payload", {}).get("subscription", {}).get("entity", {})
    sub_id = payload_entity.get("id")

    if sub_id and event in ["subscription.activated", "subscription.charged", "subscription.cancelled", "subscription.halted"]:
        sub_result = await db.execute(select(Subscription).where(Subscription.razorpay_subscription_id == sub_id))
        sub = sub_result.scalar_one_or_none()
        if sub:
            if event == "subscription.activated" or event == "subscription.charged":
                sub.status = "ACTIVE"
            elif event == "subscription.cancelled" or event == "subscription.halted":
                sub.status = "CANCELLED"

    await db.commit()
    return {"status": "ok"}
"""

with open(path, 'a') as f:
    f.write(webhook_code)

print("Restored webhook endpoint!")
