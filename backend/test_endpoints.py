import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=True)

try:
    print("--- /api/v1/predictions/RELIANCE ---")
    response = client.get("/api/v1/predictions/RELIANCE")
    print(json.dumps(response.json(), indent=2))
except Exception:
    import traceback
    traceback.print_exc()

try:
    print("\n--- /api/v1/explain/shap/RELIANCE ---")
    response = client.get("/api/v1/explain/shap/RELIANCE")
    print(json.dumps(response.json(), indent=2))
except Exception:
    import traceback
    traceback.print_exc()
