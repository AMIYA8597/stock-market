import sys
import pathlib

# Add backend directory to path
project_root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "backend"))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api():
    print("Testing /api/v1/signals/history/RELIANCE.NS...")
    resp = client.get("/api/v1/signals/history/RELIANCE.NS")
    print("Status:", resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        print("Response Keys:", list(data.keys()))
        print("Accuracy Metrics:")
        for k, v in data["accuracy_metrics"].items():
            print(f"  {k}: {v}")
    else:
        print("Error:", resp.text)

    print("\nTesting /api/v1/monitor/model-accuracy...")
    resp2 = client.get("/api/v1/monitor/model-accuracy")
    print("Status:", resp2.status_code)
    if resp2.status_code == 200:
        data2 = resp2.json()
        print("Response Keys:", list(data2.keys()))
        print("Benchmark Ensemble Accuracy:", data2["benchmark_ensemble_accuracy"])
        print("Models:")
        for model in data2["models"]:
            print(f"  {model['model_name']}: directional_accuracy={model['directional_accuracy']}")
    else:
        print("Error:", resp2.text)

if __name__ == "__main__":
    test_api()
