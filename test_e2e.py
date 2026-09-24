import requests
import time
import sys

BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://localhost:3000"

def wait_for_service(url, name, retries=10):
    print(f"Waiting for {name} at {url}...")
    for _ in range(retries):
        try:
            res = requests.get(url)
            if res.status_code in [200, 404]: # Next.js might 404 on / if localized
                print(f"{name} is UP!")
                return True
        except requests.exceptions.ConnectionError:
            time.sleep(2)
    print(f"{name} failed to start.")
    return False

def test_frontend_routes():
    print("\n--- Testing Frontend Routes ---")
    routes = [
        "/en/dashboard",
        "/en/markets/stocks/RELIANCE.NS",
        "/en/pricing",
        "/en/settings/billing",
        "/en/admin"
    ]
    all_passed = True
    for route in routes:
        res = requests.get(f"{FRONTEND_URL}{route}")
        if res.status_code == 200:
            print(f"PASS: {route}")
        else:
            print(f"FAIL: {route} (Status: {res.status_code})")
            all_passed = False
    return all_passed

def test_backend_api():
    print("\n--- Testing Backend API ---")
    all_passed = True

    # Health
    res = requests.get(f"{BACKEND_URL}/health")
    if res.status_code == 200:
        print(f"PASS: /health -> {res.json().get('status')}")
    else:
        print(f"FAIL: /health ({res.status_code})")
        all_passed = False

    # Payments Intent
    payload = {"amount": 1000.0, "method": "RAZORPAY", "currency": "INR"}
    res = requests.post(f"{BACKEND_URL}/api/v1/payments/intents", json=payload)
    if res.status_code == 200 and "intent_id" in res.json():
        print(f"PASS: /api/v1/payments/intents -> Created {res.json()['intent_id']}")
    else:
        print(f"FAIL: /api/v1/payments/intents ({res.status_code}) - {res.text}")
        all_passed = False

    # AI Predictions (Part 3)
    # Testing unauthenticated, expecting 401
    res = requests.get(f"{BACKEND_URL}/api/v1/predictions/RELIANCE.NS/latest")
    if res.status_code == 401:
        print("PASS: /api/v1/predictions/... correctly secured behind auth (401)")
    else:
        print(f"FAIL: /api/v1/predictions/... returned {res.status_code}, expected 401")
        all_passed = False

    # Market search (Part 1 Migration)
    res = requests.get(f"{BACKEND_URL}/api/v1/market/search?q=TEST")
    if res.status_code == 501:
        print("PASS: /api/v1/market/search correctly returns 501 Migration error")
    else:
        print(f"FAIL: /api/v1/market/search returned {res.status_code}, expected 501")
        all_passed = False

    return all_passed

if __name__ == "__main__":
    if not wait_for_service(f"{BACKEND_URL}/health", "Backend"):
        sys.exit(1)
    if not wait_for_service(f"{FRONTEND_URL}/", "Frontend"):
        sys.exit(1)
    
    frontend_ok = test_frontend_routes()
    backend_ok = test_backend_api()

    if frontend_ok and backend_ok:
        print("\nALL END-TO-END TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("\nSOME TESTS FAILED.")
        sys.exit(1)
