from fastapi.testclient import TestClient

from app.main import app


def test_503_response():
    print("Testing 503 MODEL_NOT_TRAINED for untrained symbol...")
    with TestClient(app) as client:
        # We know "UNTRAINED.NS" has no model artifact in the DB
        response = client.get("/api/v1/predictions/latest/UNTRAINED.NS")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")

        assert response.status_code == 503, "Expected 503 status code"
        assert response.json()["detail"]["code"] == "MODEL_NOT_TRAINED", "Expected MODEL_NOT_TRAINED code"
        print("SUCCESS: 503 MODEL_NOT_TRAINED is correctly returned.")

if __name__ == "__main__":
    test_503_response()
