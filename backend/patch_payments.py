
path = 'app/api/v1/payments.py'
with open(path, 'r') as f:
    content = f.read()

# Add webhook logging
content = content.replace("""    # 2. Log to Audit Table (regardless of verification)
    audit = BillingAuditLog(
        event_type=payload.get("event", "unknown"),
        payload_json=raw_body.decode("utf-8")[:3999],
        signature_verified=is_verified
    )
    db.add(audit)""", """    # 2. Log to Audit Table (regardless of verification)
    event_type = payload.get("event", "unknown")
    logger.info(f"Billing webhook received: event={event_type}, verified={is_verified}")
    audit = BillingAuditLog(
        event_type=event_type,
        payload_json=raw_body.decode("utf-8")[:3999],
        signature_verified=is_verified
    )
    db.add(audit)""")

with open(path, 'w') as f:
    f.write(content)
print("Payments logging patched!")
