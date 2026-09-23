from fastapi import WebSocket
from app.core.security import verify_supabase_token
from loguru import logger

async def authenticate_ws(websocket: WebSocket, token: str) -> str | None:
    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return None
    try:
        payload = verify_supabase_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008, reason="Invalid token payload")
            return None
        return user_id
    except Exception as e:
        logger.debug(f"WS auth failed: {e}")
        try:
            await websocket.close(code=1008, reason="Authentication failed")
        except:
            pass
        return None
