from fastapi import WebSocket
from app.api.v1.websocket_url import _WS_TICKETS
from loguru import logger

async def authenticate_ws(websocket: WebSocket, ticket: str) -> str | None:
    if not ticket:
        await websocket.close(code=1008, reason="Missing ticket")
        return None
    try:
        # Require single-use WebSocket tickets (no JWTs in URLs).
        user_id = _WS_TICKETS.pop(ticket, None)
        if not user_id:
            await websocket.close(code=1008, reason="Invalid or expired ticket")
            return None
        return user_id
    except Exception as e:
        logger.debug(f"WS auth failed: {e}")
        try:
            await websocket.close(code=1008, reason="Authentication failed")
        except:
            pass
        return None
