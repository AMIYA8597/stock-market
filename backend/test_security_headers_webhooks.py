import asyncio
import httpx
import json

async def test_security_headers():
    print("Testing Security Headers...")
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "http://127.0.0.1:8000/api/v1/health",
            headers={"x-forwarded-proto": "https"}
        )
        headers = res.headers

        expected = [
            "strict-transport-security",
            "x-content-type-options",
            "x-frame-options",
            "content-security-policy"
        ]

        for h in expected:
            if h in headers:
                print(f"[OK] {h} present")
            else:
                print(f"[FAIL] {h} MISSING!")

async def test_cors_enforcement():
    print("\nTesting CORS Enforcement...")
    async with httpx.AsyncClient() as client:
        # Try a forbidden origin
        res = await client.options(
            "http://127.0.0.1:8000/api/v1/health",
            headers={
                "Origin": "http://evil-cors-domain.com",
                "Access-Control-Request-Method": "GET"
            }
        )
        if res.status_code == 400 or "access-control-allow-origin" not in res.headers:
            print("[OK] CORS correctly blocked unallowed origin or did not echo it back.")
        else:
            print(f"[FAIL] CORS allowed evil origin! Allowed Origin: {res.headers.get('access-control-allow-origin')}")

async def test_webhook_signatures():
    print("\nTesting Webhook Signatures...")
    payload = {"event": "subscription.activated", "payload": {"subscription": {"entity": {"id": "sub_123"}}}}
    raw_body = json.dumps(payload).encode()

    # 1. Test with invalid signature
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "http://127.0.0.1:8000/api/v1/payments/webhook",
            content=raw_body,
            headers={"x-razorpay-signature": "invalid_sig_123"}
        )

        if res.json().get("status") == "logged_unverified":
            print("[OK] Invalid signature correctly rejected!")
        else:
            print(f"[FAIL] Webhook processed despite invalid signature! Response: {res.json()}")

async def main():
    await test_security_headers()
    await test_cors_enforcement()
    await test_webhook_signatures()

if __name__ == "__main__":
    asyncio.run(main())
