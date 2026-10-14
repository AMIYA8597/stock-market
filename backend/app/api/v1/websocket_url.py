import hashlib
import hmac
import time
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/websocket_url")

_TICKET_TTL_SECONDS = 60


def _ticket_secret() -> bytes:
    settings = get_settings()
    raw = (
        getattr(settings, "SECRET_KEY", None)
        or getattr(settings, "SUPABASE_JWT_SECRET", None)
        or "neuroquant-ws-hmac-key"
    )
    return str(raw).encode("utf-8")


def sign_ws_ticket(user_id: str, ttl_seconds: int = _TICKET_TTL_SECONDS) -> str:
    """Create a short-lived HMAC-SHA256 signed ticket usable across stateless instances."""
    exp = int(time.time()) + ttl_seconds
    nonce = uuid.uuid4().hex[:12]
    payload = f"{user_id}.{exp}.{nonce}"
    sig = hmac.new(_ticket_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def verify_ws_ticket(ticket: str) -> str | None:
    """Verify an HMAC-SHA256 signed WebSocket ticket and return user_id if valid."""
    if not ticket or "." not in ticket:
        return None
    parts = ticket.split(".")
    if len(parts) != 4:
        return None
    user_id, exp_str, nonce, sig = parts
    if not user_id or not nonce or not sig:
        return None
    try:
        exp = int(exp_str)
    except ValueError:
        return None
    if time.time() > exp:
        return None
    payload = f"{user_id}.{exp_str}.{nonce}"
    expected_sig = hmac.new(_ticket_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        return None
    return user_id


@router.get("/ws_url", tags=["debug"])
async def get_ws_url() -> dict[str, str]:
    """Return the WebSocket URL for clients.

    Allows front‑end to query the backend for the correct WS endpoint,
    which can be overridden via the `WEBSOCKET_URL` environment variable.
    """
    settings = get_settings()
    return {"ws_url": settings.WEBSOCKET_URL}


@router.post("/ticket", tags=["websocket"])
async def create_ws_ticket(user=Depends(get_current_user)) -> dict[str, str]:
    """Generate a short-lived ticket for WebSocket authentication."""
    user_id = str(getattr(user, "id", getattr(user, "user_id", "")))
    ticket = sign_ws_ticket(user_id, ttl_seconds=_TICKET_TTL_SECONDS)

    from app.database.redis_client import cache_set, get_redis_client

    try:
        redis = await get_redis_client()
        await cache_set(
            redis,
            f"ws:ticket:{ticket}",
            user_id,
            ttl=timedelta(seconds=_TICKET_TTL_SECONDS),
        )
    except Exception:
        # Stateless HMAC verification still works across all instances
        pass

    return {"ticket": ticket}
