import requests
import json

try:
    r = requests.get(
        "http://localhost:8000/api/v1/global/history/RELIANCE.NS",
        params={"interval": "1d", "period": "1y"},
        timeout=60,
    )
    print(f"Status: {r.status_code}")
    d = r.json()
    print(f"Symbol: {d.get('symbol', '?')}")
    data = d.get("data", [])
    print(f"Data points: {len(data)}")
    if data:
        print(f"First point: {json.dumps(data[0], default=str)}")
        print(f"Last point: {json.dumps(data[-1], default=str)}")
except Exception as e:
    print(f"ERROR: {e}")
