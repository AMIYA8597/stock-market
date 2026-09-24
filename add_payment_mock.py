with open('backend/app/api/v1/payments.py', 'a', encoding='utf-8') as f:
    f.write('''
class IntentPayload(BaseModel):
    amount: float
    method: str
    currency: str = "INR"
    description: str | None = None

@router.post("/intents")
async def create_intent(payload: IntentPayload):
    return {
        "intent_id": f"pi_{uuid.uuid4().hex[:10]}",
        "provider_ref": "mock_provider_ref",
        "amount": str(payload.amount),
        "status": "created"
    }

@router.post("/confirm")
async def confirm_intent(intent_id: str = "", razorpay_payment_id: str = ""):
    return {
        "intent_id": intent_id,
        "status": "success",
        "credited_amount": "0",
        "completed_at": datetime.now(timezone.utc).isoformat()
    }
''')
