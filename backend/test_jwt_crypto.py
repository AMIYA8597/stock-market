import asyncio
import base64
import json
from datetime import UTC, datetime, timedelta

import httpx


async def main():
    print("Testing JWT alg: none rejection...")

    header = {"typ": "JWT", "alg": "none"}
    payload = {
        "sub": "00000000-0000-0000-0000-000000000000",
        "type": "access",
        "exp": int((datetime.now(UTC) + timedelta(minutes=15)).timestamp())
    }

    header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")

    forged_token = f"{header_b64}.{payload_b64}."

    async with httpx.AsyncClient() as client:
        res = await client.get("http://127.0.0.1:8000/api/v1/portfolio", headers={"Authorization": f"Bearer {forged_token}"})

        print(f"alg: none response: {res.status_code}")
        if res.status_code == 401:
            print("SUCCESS: alg: none token was correctly rejected!")
        else:
            print(f"FAILED: Expected 401, got {res.status_code}")

if __name__ == "__main__":
    asyncio.run(main())
