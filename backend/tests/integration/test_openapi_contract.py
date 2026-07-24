import json

from fastapi.testclient import TestClient

from app.main import app


def test_openapi_schema_dump():
    """Dump the OpenAPI schema to backend/openapi.json for frontend typings generation."""
    client = TestClient(app)
    response = client.get("/api/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema

    with open("openapi.json", "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
