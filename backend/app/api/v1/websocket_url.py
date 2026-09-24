from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/websocket_url")


@router.get("/ws_url", tags=["debug"])
async def get_ws_url() -> dict[str, str]:
    """Return the WebSocket URL for clients.

    Allows front‑end to query the backend for the correct WS endpoint,
    which can be overridden via the `WEBSOCKET_URL` environment variable.
    """
    settings = get_settings()
    return {"ws_url": settings.WEBSOCKET_URL}

import uuid
import asyncio
from fastapi import Depends
from app.core.dependencies import get_current_user

# Global in-memory ticket store (UUID -> user_id)
# In production, use Redis with TTL
_WS_TICKETS: dict[str, str] = {}

@router.post("/ticket", tags=["websocket"])
async def create_ws_ticket(user = Depends(get_current_user)) -> dict[str, str]:
    """Generate a short-lived ticket for WebSocket authentication."""
    ticket = str(uuid.uuid4())
    _WS_TICKETS[ticket] = str(user.id)
    
    # Auto-expire ticket after 30 seconds
    async def expire_ticket(t: str):
        await asyncio.sleep(30)
        _WS_TICKETS.pop(t, None)
    
    asyncio.create_task(expire_ticket(ticket))
    return {"ticket": ticket}
