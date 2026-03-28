from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.router import api_router


app = FastAPI()
app.include_router(api_router, prefix="/api/v1")
client = TestClient(app)


def test_auth_login_alias_and_profile_logout() -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "trader@example.com", "password": "S3curePass!123"},
    )
    assert login.status_code == 200
    token_payload = login.json()
    assert "access_token" in token_payload

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    me_payload = me.json()
    assert "email" in me_payload
    assert me_payload["is_active"] is True

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
