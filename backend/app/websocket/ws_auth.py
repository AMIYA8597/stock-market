from fastapi import WebSocket
from loguru import logger

from app.api.v1.websocket_url import verify_ws_ticket
from app.core.security import verify_supabase_token


async def authenticate_ws(
    websocket: WebSocket, token: str, allow_anonymous: bool = False
) -> str | None:
    if not token:
        if allow_anonymous:
            return "anonymous"
        await websocket.close(code=1008, reason="Missing token")
        return None

    # 1. Check HMAC-signed stateless ticket
    hmac_user_id = verify_ws_ticket(token)
    if hmac_user_id:
        try:
            from app.database.redis_client import get_redis_client

            redis = await get_redis_client()
            await redis.delete(f"ws:ticket:{token}")
        except Exception:
            pass
        return hmac_user_id

    # 2. Check Redis-stored ticket
    try:
        from app.database.redis_client import cache_get, get_redis_client

        redis = await get_redis_client()
        ticket_key = f"ws:ticket:{token}"
        cached_user_id = await cache_get(redis, ticket_key)
        if cached_user_id:
            await redis.delete(ticket_key)
            return str(cached_user_id)
    except Exception:
        pass

    # 3. Check raw Supabase JWT
    try:
        payload = verify_supabase_token(token)
        user_id = payload.get("sub")
        if user_id:
            return str(user_id)
        if allow_anonymous:
            return "anonymous"
        await websocket.close(code=1008, reason="Invalid token payload")
        return None
    except Exception as e:
        logger.debug(f"WS auth failed: {e}")
        if allow_anonymous:
            return "anonymous"
        try:
            await websocket.close(code=1008, reason="Authentication failed")
        except Exception:
            pass
        return None
