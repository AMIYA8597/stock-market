import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

def main():
    print("Testing 503 MODEL_NOT_TRAINED path for UNKNOWN.NS...")

    with TestClient(app) as client:
        response = client.get("/api/v1/predictions/UNKNOWN.NS")
        print(f"Status Code: {response.status_code}")
        print(f"Response JSON: {response.json()}")

if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    main()
