"""MongoDB async connection client and collection CRUD helpers.

Integrates with motor to connect to a remote or local MongoDB database instance.
Contains collections for users, refresh_sessions, portfolios, transactions, alerts,
paper-trading wallet state, and cached market snapshots.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import yfinance as yf
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import get_settings

logger = logging.getLogger("app.database.mongodb")
settings = get_settings()

client: AsyncIOMotorClient | None = None
db: Any = None
_client_loop: Any = None

# Circuit Breaker state
_mongo_online: bool = True
_mongo_cooldown_until: datetime | None = None


def trip_circuit(exc: Exception | None = None) -> None:
    """Trip the MongoDB circuit breaker and initiate cooling-down period."""
    global _mongo_online, _mongo_cooldown_until
    if _mongo_online:
        logger.warning(
            f"🚨 Tripping MongoDB circuit breaker. Bypassing MongoDB operations. Reason: {exc}"
        )
        _mongo_online = False
    _mongo_cooldown_until = datetime.now(UTC) + timedelta(minutes=5)


def get_mongo_db() -> Any:
    """Return initialized MongoDB database instance if MONGODB_URL is configured."""
    global client, db, _client_loop, _mongo_online, _mongo_cooldown_until
    import asyncio

    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    # Check if circuit is open
    if not _mongo_online:
        if _mongo_cooldown_until and datetime.now(UTC) > _mongo_cooldown_until:
            logger.info("♻️ Cooldown expired. Retrying MongoDB connection...")
            _mongo_online = True
            _mongo_cooldown_until = None
        else:
            return None

    if client is not None and _client_loop is not None and current_loop != _client_loop:
        logger.debug("🔄 Event loop changed/restarted. Re-initializing AsyncIOMotorClient.")
        client = None
        db = None

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

            # Limit server selection timeout to 1.5s for fast fallback
            client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=1500, connectTimeoutMS=1500)
            _client_loop = current_loop
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
            _client_loop = None
            trip_circuit(e)
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
        trip_circuit(e)
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
        trip_circuit(e)
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
    try:
        await database.users.insert_one(doc)
        return doc
    except Exception as e:
        logger.error(f"mongo_create_user_error: {e}")
        trip_circuit(e)
        raise RuntimeError("MongoDB create user failure") from e


async def mongo_update_user(user_id: str, update_data: dict[str, Any]) -> bool:
    database = get_mongo_db()
    if database is None:
        return False
    try:
        await database.users.update_one({"_id": user_id}, {"$set": update_data})
        return True
    except Exception as e:
        logger.error(f"mongo_update_user_error: {e}")
        trip_circuit(e)
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
    try:
        await database.refresh_sessions.insert_one(doc)
    except Exception as e:
        logger.error(f"mongo_save_refresh_session_error: {e}")
        trip_circuit(e)


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
        trip_circuit(e)
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
        trip_circuit(e)


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
        trip_circuit(e)


# ─── Portfolio & holdings Collection CRUD Helpers ─────────────────────────

async def mongo_get_portfolio(user_id: str) -> dict[str, Any]:
    database = get_mongo_db()
    if database is None:
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
        trip_circuit(e)
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
        trip_circuit(e)
        return False


async def mongo_add_transaction(user_id: str, symbol: str, tx_type: str, quantity: float, price: float, net_amount: float) -> dict[str, Any]:
    database = get_mongo_db()
    fallback_doc = {
        "transaction_id": str(uuid4()),
        "symbol": symbol.upper(),
        "type": tx_type.upper(),
        "quantity": float(quantity),
        "price": float(price),
        "net_amount": float(net_amount),
        "timestamp": datetime.now(UTC)
    }
    if database is None:
        return fallback_doc

    try:
        doc = {
            "_id": fallback_doc["transaction_id"],
            "user_id": user_id,
            "symbol": fallback_doc["symbol"],
            "type": fallback_doc["type"],
            "quantity": fallback_doc["quantity"],
            "price": fallback_doc["price"],
            "net_amount": fallback_doc["net_amount"],
            "timestamp": fallback_doc["timestamp"],
        }
        await database.transactions.insert_one(doc)
        doc["transaction_id"] = doc["_id"]
        return doc
    except Exception as e:
        logger.error(f"mongo_add_transaction_error: {e}")
        trip_circuit(e)
        return fallback_doc


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
        trip_circuit(e)
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
        raise RuntimeError(f"Unable to fetch live price for {sym}") from e


async def mongo_get_wallet_state(user_id: str) -> dict[str, Any]:
    database = get_mongo_db()
    default_state = {
        "user_id": user_id,
        "currency": "INR",
        "wallet_balance": "0.00",
        "updated_at": datetime.now(UTC),
    }
    if database is None:
        return default_state

    try:
        wallet = await database.paper_wallets.find_one({"user_id": user_id})
        if wallet is None:
            wallet = {
                "_id": str(uuid4()),
                **default_state,
                "created_at": datetime.now(UTC),
            }
            await database.paper_wallets.insert_one(wallet)
        wallet["wallet_balance"] = str(Decimal(str(wallet.get("wallet_balance", "0.00"))).quantize(Decimal("0.01")))
        return wallet
    except Exception as e:
        logger.error(f"mongo_get_wallet_state_error: {e}")
        trip_circuit(e)
        return default_state


async def mongo_credit_wallet(
    user_id: str,
    amount: Decimal,
    method: str,
    description: str,
    idempotency_key: str,
) -> dict[str, Any]:
    database = get_mongo_db()
    credited_amount = amount.quantize(Decimal("0.01"))
    now = datetime.now(UTC)
    fallback = {
        "intent_id": f"pi_{uuid4().hex}",
        "payment_id": f"pay_{uuid4().hex}",
        "provider_ref": f"paper_{uuid4().hex[:18]}",
        "amount": str(credited_amount),
        "currency": "INR",
        "method": method,
        "status": "succeeded",
        "wallet_balance": str(credited_amount),
        "description": description,
        "created_at": now,
        "completed_at": now,
    }
    if database is None:
        return fallback

    try:
        existing = await database.paper_payments.find_one(
            {"user_id": user_id, "idempotency_key": idempotency_key}
        )
        if existing is not None:
            existing["wallet_balance"] = str(existing.get("wallet_balance", existing.get("amount", "0.00")))
            return existing

        wallet = await mongo_get_wallet_state(user_id)
        current_balance = Decimal(str(wallet.get("wallet_balance", "0.00")))
        next_balance = (current_balance + credited_amount).quantize(Decimal("0.01"))

        payment_doc = {
            "_id": f"pay_{uuid4().hex}",
            "intent_id": f"pi_{uuid4().hex}",
            "provider_ref": f"paper_{uuid4().hex[:18]}",
            "user_id": user_id,
            "idempotency_key": idempotency_key,
            "amount": str(credited_amount),
            "currency": "INR",
            "method": method,
            "status": "succeeded",
            "wallet_balance": str(next_balance),
            "description": description,
            "created_at": now,
            "completed_at": now,
        }
        await database.paper_payments.insert_one(payment_doc)
        await database.paper_wallets.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "currency": "INR",
                    "wallet_balance": str(next_balance),
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "_id": str(uuid4()),
                    "created_at": now,
                },
            },
            upsert=True,
        )
        return payment_doc
    except Exception as e:
        logger.error(f"mongo_credit_wallet_error: {e}")
        trip_circuit(e)
        return fallback


async def mongo_create_payment_intent(
    user_id: str,
    amount: Decimal,
    currency: str,
    method: str,
    description: str,
    idempotency_key: str,
) -> dict[str, Any]:
    database = get_mongo_db()
    now = datetime.now(UTC)
    normalized_amount = amount.quantize(Decimal("0.01"))
    fallback = {
        "intent_id": f"pi_{uuid4().hex}",
        "provider_ref": f"paper_{uuid4().hex[:18]}",
        "user_id": user_id,
        "idempotency_key": idempotency_key,
        "amount": str(normalized_amount),
        "currency": currency,
        "method": method,
        "description": description,
        "status": "requires_confirmation",
        "created_at": now,
    }
    if database is None:
        return fallback

    try:
        existing = await database.paper_payment_intents.find_one(
            {"user_id": user_id, "idempotency_key": idempotency_key}
        )
        if existing is not None:
            return existing

        doc = {
            "_id": str(uuid4()),
            **fallback,
        }
        await database.paper_payment_intents.insert_one(doc)
        return doc
    except Exception as e:
        logger.error(f"mongo_create_payment_intent_error: {e}")
        trip_circuit(e)
        return fallback


async def mongo_get_payment_intent(user_id: str, intent_id: str) -> dict[str, Any] | None:
    database = get_mongo_db()
    if database is None:
        return None
    try:
        return await database.paper_payment_intents.find_one(
            {"user_id": user_id, "intent_id": intent_id}
        )
    except Exception as e:
        logger.error(f"mongo_get_payment_intent_error: {e}")
        trip_circuit(e)
        return None


async def mongo_get_payment_history(user_id: str, limit: int = 20) -> list[dict[str, Any]]:
    database = get_mongo_db()
    if database is None:
        return []
    try:
        cursor = database.paper_payments.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
        return await cursor.to_list(length=limit)
    except Exception as e:
        logger.error(f"mongo_get_payment_history_error: {e}")
        trip_circuit(e)
        return []


async def mongo_cache_market_payload(
    cache_type: str,
    cache_key: str,
    payload: dict[str, Any] | list[dict[str, Any]],
    ttl_seconds: int = 300,
) -> None:
    database = get_mongo_db()
    if database is None:
        return
    now = datetime.now(UTC)
    try:
        await database.market_cache.update_one(
            {"cache_type": cache_type, "cache_key": cache_key},
            {
                "$set": {
                    "payload": payload,
                    "updated_at": now,
                    "expires_at": now + timedelta(seconds=ttl_seconds),
                },
                "$setOnInsert": {"_id": str(uuid4())},
            },
            upsert=True,
        )
    except Exception as e:
        logger.error(f"mongo_cache_market_payload_error: {e}")
        trip_circuit(e)


async def mongo_get_market_payload(cache_type: str, cache_key: str) -> dict[str, Any] | list[dict[str, Any]] | None:
    database = get_mongo_db()
    if database is None:
        return None
    try:
        doc = await database.market_cache.find_one(
            {
                "cache_type": cache_type,
                "cache_key": cache_key,
                "expires_at": {"$gt": datetime.now(UTC)},
            }
        )
        if doc is None:
            return None
        return doc.get("payload")
    except Exception as e:
        logger.error(f"mongo_get_market_payload_error: {e}")
        trip_circuit(e)
        return None


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
        trip_circuit(e)
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
    try:
        await database.alerts.insert_one(doc)
        return doc
    except Exception as e:
        logger.error(f"mongo_create_alert_error: {e}")
        trip_circuit(e)
        raise RuntimeError("MongoDB create alert failure") from e


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
        trip_circuit(e)
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
        trip_circuit(e)
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
        trip_circuit(e)
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
    try:
        await database.notifications.insert_one(doc)
        return doc
    except Exception as e:
        logger.error(f"mongo_create_notification_error: {e}")
        trip_circuit(e)
        raise RuntimeError("MongoDB create notification failure") from e


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
        trip_circuit(e)
        return False
