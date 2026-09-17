import asyncio
import uuid
import warnings
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.dependencies import get_current_user, get_current_user_or_none, require_premium_tier

warnings.filterwarnings("ignore")

class MockUser(dict):
    def __init__(self, role="USER"):
        uid = uuid.uuid4()
        super().__init__({"sub": str(uid)})
        self.id = uid
        self.role = role

current_mock_user = None

def get_mock_user():
    return current_mock_user

def mock_require_premium_tier(feature_flag: str):
    async def _checker():
        return get_mock_user()
    return _checker

app.dependency_overrides[get_current_user] = get_mock_user
app.dependency_overrides[get_current_user_or_none] = get_mock_user
app.dependency_overrides[require_premium_tier] = mock_require_premium_tier

async def run_tests():
    global current_mock_user
    user_a = MockUser(role="USER")
    user_b = MockUser(role="USER")

    transport = ASGITransport(app=app)

    # SETUP USER B
    current_mock_user = user_b
    async with AsyncClient(transport=transport, base_url="http://test") as ac_b:
        print("--- Setting up User B's resources ---")

        # Journal
        resp = await ac_b.post("/api/v1/journal", json={"symbol": "AAPL", "notes": "B", "tags": "swing", "rating": 3, "entry_price": 100, "exit_price": 110, "quantity": 10, "direction": "LONG"})
        journal_b_id = resp.json().get("id", "UNKNOWN")

        # Alert
        resp = await ac_b.post("/api/v1/alerts", json={"symbol": "AAPL", "alert_type": "PRICE_ABOVE", "threshold": 150, "name": "B alert", "enabled": True})
        alert_b_id = resp.json().get("id", "UNKNOWN")

        # Backtest
        resp = await ac_b.post("/api/v1/backtest/run", json={"strategy_name": "strat", "strategy_params": {}, "universe": ["AAPL"], "date_from": "2025-01-01", "date_to": "2025-02-01", "initial_capital": 100000})
        backtest_b_id = resp.json().get("job_id", "UNKNOWN")

        print(f"Created resources for B: Journal {journal_b_id}, Alert {alert_b_id}, Backtest {backtest_b_id}")

    # TEST WITH USER A
    current_mock_user = user_a
    async with AsyncClient(transport=transport, base_url="http://test") as ac_a:
        print("\n--- BOLA TESTS (User A trying to access User B's resources) ---")

        resp = await ac_a.delete(f"/api/v1/journal/{journal_b_id}")
        print(f"Delete Journal B (by A): Status {resp.status_code}")

        resp = await ac_a.delete(f"/api/v1/alerts/{alert_b_id}")
        print(f"Delete Alert B (by A): Status {resp.status_code}")

        resp = await ac_a.get(f"/api/v1/backtest/status/{backtest_b_id}")
        print(f"Get Backtest B Status (by A): Status {resp.status_code}")

        print("\n--- BFLA TESTS (Non-admin User A trying to access Admin endpoints) ---")
        resp = await ac_a.get("/api/v1/admin/users")
        print(f"Get Admin Users (by A): Status {resp.status_code}")

        resp = await ac_a.get("/api/v1/admin/content")
        print(f"Get Admin Content (by A): Status {resp.status_code}")

        print("\n--- Quantedge Router Ownership Tests ---")
        resp = await ac_a.get("/api/paper-trade/portfolio")
        print(f"Get Paper Portfolio (by A): Status {resp.status_code}")

if __name__ == "__main__":
    asyncio.run(run_tests())
