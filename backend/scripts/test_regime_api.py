import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_api():
    # A is a symbol we know is in the DB
    response = client.get("/api/v1/regime/A/current")
    print(f"Status Code: {response.status_code}")
    print(f"Response JSON: {response.json()}")

if __name__ == "__main__":
    test_api()
