import requests
import time

base_url = "http://127.0.0.1:8000"

def test_backend():
    print("Testing Backend...")
    # Test Market Search
    print("\n1. Testing Market Search")
    res = requests.get(f"{base_url}/api/v1/market/search?q=REL")
    print(f"Search Response: {res.status_code}")

    # Test Payments - Create Intent
    print("\n2. Testing Payments - Create Intent")
    payload = {
        "amount": 500.0,
        "method": "RAZORPAY",
        "currency": "INR",
        "description": "Wallet Top-up"
    }
    # Intentionally testing without auth (should 401 or work depending on deps)
    res = requests.post(f"{base_url}/api/v1/payments/intents", json=payload)
    print(f"Create Intent Response: {res.status_code} - {res.text}")
    
    # Test Websocket Ticket
    print("\n3. Testing WebSocket Ticket Endpoint")
    res = requests.post(f"{base_url}/api/v1/websocket_url/ticket")
    print(f"WS Ticket Response: {res.status_code}")

if __name__ == "__main__":
    test_backend()
