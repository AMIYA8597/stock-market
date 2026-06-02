"""MongoDB async connection client and collection CRUD helpers.

Integrates with motor to connect to a remote or local MongoDB database instance.
Contains collections for users, refresh_sessions, portfolios, transactions, and alerts.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import yfinance as yf
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings

logger = logging.getLogger("app.database.mongodb")
settings = get_settings()

client: AsyncIOMotorClient | None = None
db: Any = None


def get_mongo_db() -> Any:
    """Return initialized MongoDB database instance if MONGODB_URL is configured."""
    global client, db
    if client is None and settings.MONGODB_URL:
        try:
            import urllib.parse
            url = settings.MONGODB_URL
            if url.startswith("mongodb+srv://") or url.startswith("mongodb://"):
                prefix, rest = url.split("://", 1)
                if "@" in rest:
                    creds, host_part = rest.rsplit("@", 1)
                    if ":" in creds:
                        username, password = creds.split(":", 1)
                        unquoted_user = urllib.parse.unquote(username)
                        unquoted_pass = urllib.parse.unquote(password)
                        encoded_user = urllib.parse.quote_plus(unquoted_user)
                        encoded_pass = urllib.parse.quote_plus(unquoted_pass)
                        url = f"{prefix}://{encoded_user}:{encoded_pass}@{host_part}"
            client = AsyncIOMotorClient(url)
            try:
                db_name = client.get_default_database().name
                if not db_name:
                    db_name = "neuroquant"
            except Exception:
                db_name = "neuroquant"
            db = client[db_name]
            logger.info(f"💾 Connected to MongoDB database: '{db_name}'")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}", exc_info=True)
            db = None
    return db


# ─── User Collection CRUD Helpers ────────────────────────────────────────

async def mongo_get_user_by_email(email: str) -> dict[str, Any] | None:
    database = get_mongo_db()
    if database is None:
        return None
    try:
        user = await database.users.find_one({"email": email.lower().strip()})
        return user
    except Exception as e:
        logger.error(f"mongo_get_user_by_email_error: {e}")
        return None


async def mongo_get_user_by_id(user_id: str) -> dict[str, Any] | None:
    database = get_mongo_db()
    if database is None:
        return None
    try:
        user = await database.users.find_one({"_id": user_id})
        return user
    except Exception as e:
        logger.error(f"mongo_get_user_by_id_error: {e}")
        return None


async def mongo_create_user(user_data: dict[str, Any]) -> dict[str, Any]:
    database = get_mongo_db()
    if database is None:
        raise RuntimeError("MongoDB not initialized")

    doc = {
        "_id": user_data.get("id") or str(uuid4()),
        "email": user_data["email"].lower().strip(),
        "hashed_password": user_data["hashed_password"],
        "full_name": user_data.get("full_name"),
        "role": user_data.get("role", "USER"),
        "is_active": user_data.get("is_active", True),
        "created_at": user_data.get("created_at") or datetime.now(UTC),
        "failed_login_attempts": 0,
        "locked_until": None,
        "last_login_at": None,
    }
    await database.users.insert_one(doc)
    return doc


async def mongo_update_user(user_id: str, update_data: dict[str, Any]) -> bool:
    database = get_mongo_db()
    if database is None:
        return False
    try:
        await database.users.update_one({"_id": user_id}, {"$set": update_data})
        return True
    except Exception as e:
        logger.error(f"mongo_update_user_error: {e}")
        return False


# ─── Refresh Session Collection CRUD Helpers ──────────────────────────────

async def mongo_save_refresh_session(session_data: dict[str, Any]) -> None:
    database = get_mongo_db()
    if database is None:
        return
    doc = {
        "_id": str(uuid4()),
        "user_id": session_data["user_id"],
        "token_hash": session_data["token_hash"],
        "family_id": session_data["family_id"],
        "expires_at": session_data["expires_at"],
        "created_at": datetime.now(UTC),
        "revoked_at": None,
    }
    await database.refresh_sessions.insert_one(doc)


async def mongo_get_refresh_session(token_hash: str) -> dict[str, Any] | None:
    database = get_mongo_db()
    if database is None:
        return None
    try:
        session = await database.refresh_sessions.find_one({
            "token_hash": token_hash,
            "revoked_at": None,
            "expires_at": {"$gt": datetime.now(UTC)}
        })
        return session
    except Exception as e:
        logger.error(f"mongo_get_refresh_session_error: {e}")
        return None


async def mongo_revoke_refresh_session_family(family_id: str) -> None:
    database = get_mongo_db()
    if database is None:
        return
    try:
        await database.refresh_sessions.update_many(
            {"family_id": family_id},
            {"$set": {"revoked_at": datetime.now(UTC)}}
        )
    except Exception as e:
        logger.error(f"mongo_revoke_refresh_session_family_error: {e}")


async def mongo_revoke_user_sessions(user_id: str) -> None:
    database = get_mongo_db()
    if database is None:
        return
    try:
        await database.refresh_sessions.update_many(
            {"user_id": user_id, "revoked_at": None},
            {"$set": {"revoked_at": datetime.now(UTC)}}
        )
    except Exception as e:
        logger.error(f"mongo_revoke_user_sessions_error: {e}")


# ─── Portfolio & holdings Collection CRUD Helpers ─────────────────────────

async def mongo_get_portfolio(user_id: str) -> dict[str, Any]:
    database = get_mongo_db()
    if database is None:
        # Fallback dictionary if Mongo is unavailable
        return {"user_id": user_id, "cash_balance": 1000000.0, "holdings": []}

    try:
        portfolio = await database.portfolios.find_one({"user_id": user_id})
        if not portfolio:
            # Create default portfolio
            portfolio = {
                "_id": str(uuid4()),
                "user_id": user_id,
                "cash_balance": 1000000.0,
                "holdings": [],
                "created_at": datetime.now(UTC),
            }
            await database.portfolios.insert_one(portfolio)
        return portfolio
    except Exception as e:
        logger.error(f"mongo_get_portfolio_error: {e}")
        return {"user_id": user_id, "cash_balance": 1000000.0, "holdings": []}


async def mongo_save_portfolio(user_id: str, cash_balance: float, holdings: list[dict[str, Any]]) -> bool:
    database = get_mongo_db()
    if database is None:
        return False
    try:
        await database.portfolios.update_one(
            {"user_id": user_id},
            {"$set": {
                "cash_balance": float(cash_balance),
                "holdings": holdings,
                "updated_at": datetime.now(UTC)
            }},
            upsert=True
        )
        return True
    except Exception as e:
        logger.error(f"mongo_save_portfolio_error: {e}")
        return False


async def mongo_add_transaction(user_id: str, symbol: str, tx_type: str, quantity: float, price: float, net_amount: float) -> dict[str, Any]:
    database = get_mongo_db()
    if database is None:
        # Mock transaction doc
        return {
            "transaction_id": str(uuid4()),
            "symbol": symbol.upper(),
            "type": tx_type,
            "quantity": quantity,
            "price": price,
            "net_amount": net_amount,
            "timestamp": datetime.now(UTC)
        }

    doc = {
        "_id": str(uuid4()),
        "user_id": user_id,
        "symbol": symbol.upper(),
        "type": tx_type.upper(),
        "quantity": float(quantity),
        "price": float(price),
        "net_amount": float(net_amount),
        "timestamp": datetime.now(UTC),
    }
    await database.transactions.insert_one(doc)
    doc["transaction_id"] = doc["_id"]
    return doc


async def mongo_get_transactions(user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    database = get_mongo_db()
    if database is None:
        return []
    try:
        cursor = database.transactions.find({"user_id": user_id}).sort("timestamp", -1).limit(limit)
        results = await cursor.to_list(length=limit)
        for r in results:
            r["transaction_id"] = r["_id"]
        return results
    except Exception as e:
        logger.error(f"mongo_get_transactions_error: {e}")
        return []


# Simple in-memory cache for stock prices
_PRICE_CACHE: dict[str, tuple[float, datetime]] = {}

async def get_live_price(symbol: str) -> float:
    # Use clean symbol
    sym = symbol.upper().strip()
    now = datetime.now(UTC)

    # Cache hit check (expire after 30 seconds)
    if sym in _PRICE_CACHE:
        val, ts = _PRICE_CACHE[sym]
        if (now - ts).total_seconds() < 30:
            return val

    # Try fetching via yfinance
    try:
        def _fetch():
            ticker = yf.Ticker(sym)
            fast = ticker.fast_info
            if fast and hasattr(fast, "last_price") and fast.last_price is not None:
                return float(fast.last_price)
            # Fallback to history
            hist = ticker.history(period="1d")
            if not hist.empty:
                return float(hist.iloc[-1]["Close"])
            return 100.0

        import asyncio
        price = await asyncio.to_thread(_fetch)
        _PRICE_CACHE[sym] = (price, now)
        return price
    except Exception as e:
        logger.warning(f"Error fetching live price for {sym}: {e}")
        # Default fallback values for major tickers
        fallbacks = {
            "RELIANCE.NS": 2521.30,
            "TCS.NS": 4242.70,
            "INFY.NS": 1610.0,
            "HDFCBANK.NS": 1580.0,
        }
        return fallbacks.get(sym, 100.0)


# ─── Alert Collection CRUD Helpers ───────────────────────────────────────

async def mongo_get_alerts(user_id: str) -> list[dict[str, Any]]:
    database = get_mongo_db()
    if database is None:
        return []
    try:
        cursor = database.alerts.find({"user_id": user_id})
        results = await cursor.to_list(length=100)
        return results
    except Exception as e:
        logger.error(f"mongo_get_alerts_error: {e}")
        return []


async def mongo_create_alert(user_id: str, alert_data: dict[str, Any]) -> dict[str, Any]:
    database = get_mongo_db()
    if database is None:
        raise RuntimeError("MongoDB not initialized")
    doc = {
        "_id": str(uuid4()),
        "user_id": user_id,
        "symbol": alert_data["symbol"].upper().strip(),
        "alert_type": alert_data["alert_type"],
        "threshold": float(alert_data["threshold"]),
        "name": alert_data.get("name") or f"{alert_data['symbol']} alert",
        "enabled": alert_data.get("enabled", True),
        "is_triggered": False,
        "triggered_at": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC)
    }
    await database.alerts.insert_one(doc)
    return doc


async def mongo_update_alert(user_id: str, alert_id: str, update_data: dict[str, Any]) -> dict[str, Any] | None:
    database = get_mongo_db()
    if database is None:
        return None
    try:
        # Convert any Decimal or numeric values
        set_dict = {}
        for k, v in update_data.items():
            if k == "threshold" and v is not None:
                set_dict[k] = float(v)
            elif k in {"name", "enabled", "is_triggered"} and v is not None:
                set_dict[k] = v
        
        set_dict["updated_at"] = datetime.now(UTC)
        await database.alerts.update_one(
            {"_id": alert_id, "user_id": user_id},
            {"$set": set_dict}
        )
        updated = await database.alerts.find_one({"_id": alert_id, "user_id": user_id})
        return updated
    except Exception as e:
        logger.error(f"mongo_update_alert_error: {e}")
        return None


async def mongo_delete_alert(user_id: str, alert_id: str) -> bool:
    database = get_mongo_db()
    if database is None:
        return False
    try:
        res = await database.alerts.delete_one({"_id": alert_id, "user_id": user_id})
        return res.deleted_count > 0
    except Exception as e:
        logger.error(f"mongo_delete_alert_error: {e}")
        return False


# ─── Notification Collection CRUD Helpers ────────────────────────────────

async def mongo_get_notifications(user_id: str) -> list[dict[str, Any]]:
    database = get_mongo_db()
    if database is None:
        return []
    try:
        cursor = database.notifications.find({"user_id": user_id}).sort("created_at", -1)
        results = await cursor.to_list(length=100)
        return results
    except Exception as e:
        logger.error(f"mongo_get_notifications_error: {e}")
        return []


async def mongo_create_notification(notification_data: dict[str, Any]) -> dict[str, Any]:
    database = get_mongo_db()
    if database is None:
        raise RuntimeError("MongoDB not initialized")
    doc = {
        "_id": str(uuid4()),
        "user_id": notification_data["user_id"],
        "title": notification_data["title"],
        "message": notification_data["message"],
        "level": notification_data.get("level", "info"),
        "is_read": False,
        "created_at": datetime.now(UTC),
        "read_at": None
    }
    await database.notifications.insert_one(doc)
    return doc


async def mongo_mark_notification_read(user_id: str, notification_id: str) -> bool:
    database = get_mongo_db()
    if database is None:
        return False
    try:
        res = await database.notifications.update_one(
            {"_id": notification_id, "user_id": user_id},
            {"$set": {"is_read": True, "read_at": datetime.now(UTC)}}
        )
        return res.modified_count > 0
    except Exception as e:
        logger.error(f"mongo_mark_notification_read_error: {e}")
        return False


