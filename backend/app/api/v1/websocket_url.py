from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/ws_url", tags=["debug"])
async def get_ws_url() -> dict[str, str]:
    """Return the WebSocket URL for clients.

    Allows front‑end to query the backend for the correct WS endpoint,
    which can be overridden via the `WEBSOCKET_URL` environment variable.
    """
    settings = get_settings()
    return {"ws_url": settings.WEBSOCKET_URL}
