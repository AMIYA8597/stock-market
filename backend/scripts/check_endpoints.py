import asyncio
import json

import httpx


async def check_endpoints():
    base_url = "http://127.0.0.1:8000/api/v1"

    endpoints = {
        "/predictions/latest/RELIANCE.NS": base_url + "/predictions/latest/RELIANCE.NS",
        "/regime/RELIANCE.NS/current": base_url + "/regime/RELIANCE.NS/current",
        "/explain/shap/RELIANCE.NS": base_url + "/explain/shap/RELIANCE.NS",
    }

    async with httpx.AsyncClient() as client:
        for name, url in endpoints.items():
            try:
                resp = await client.get(url, timeout=60.0)
                print(f"--- {name} ---")
                print(f"Status: {resp.status_code}")
                try:
                    data = resp.json()
                    # Print first 500 chars to avoid huge outputs
                    print(json.dumps(data, indent=2)[:500] + "...\n")
                except ValueError:
                    print(resp.text[:500] + "...\n")
            except Exception as e:
                print(f"--- {name} ---")
                print(f"Error: {e}\n")

if __name__ == "__main__":
    asyncio.run(check_endpoints())
