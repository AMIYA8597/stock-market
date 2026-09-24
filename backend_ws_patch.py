import re
import os

# 1. Add /ticket to api/v1/websocket_url.py
with open("backend/app/api/v1/websocket_url.py", "r", encoding="utf-8") as f:
    ws_url = f.read()

ticket_code = """
import uuid
import asyncio
from fastapi import Depends
from app.core.dependencies import get_current_user

# Global in-memory ticket store (UUID -> user_id)
# In production, use Redis with TTL
_WS_TICKETS: dict[str, str] = {}

@router.post("/ticket", tags=["websocket"])
async def create_ws_ticket(user = Depends(get_current_user)) -> dict[str, str]:
    \"\"\"Generate a short-lived ticket for WebSocket authentication.\"\"\"
    ticket = str(uuid.uuid4())
    _WS_TICKETS[ticket] = str(user.id)
    
    # Auto-expire ticket after 30 seconds
    async def expire_ticket(t: str):
        await asyncio.sleep(30)
        _WS_TICKETS.pop(t, None)
    
    asyncio.create_task(expire_ticket(ticket))
    return {"ticket": ticket}
"""

if "def create_ws_ticket" not in ws_url:
    ws_url += ticket_code
    with open("backend/app/api/v1/websocket_url.py", "w", encoding="utf-8") as f:
        f.write(ws_url)


# 2. Add /stream to websocket/router.py
with open("backend/app/websocket/router.py", "r", encoding="utf-8") as f:
    ws_router = f.read()

stream_code = """
@router.websocket("/stream")
async def ws_stream(websocket: WebSocket, ticket: str = ""):
    from app.api.v1.websocket_url import _WS_TICKETS
    user_id = _WS_TICKETS.pop(ticket, None)
    if not user_id:
        await websocket.close(code=1008)
        return
        
    manager = get_connection_manager()
    await manager.connect(websocket)
    
    # Subscribe to personal alerts by default
    await manager.subscribe(websocket, f"alerts:{user_id}")
    await manager.subscribe(websocket, "signals:alerts")
    
    # Track subscriptions for this unified connection
    subscribed_symbols: set[str] = set()
    
    try:
        while True:
            try:
                payload = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                action = str(payload.get("action", "")).lower()
                channel = str(payload.get("channel", "")).lower()
                symbols = [str(s).upper() for s in payload.get("symbols", [])]
                
                if action == "subscribe":
                    if channel == "prices":
                        for symbol in symbols:
                            await manager.subscribe(websocket, f"prices:{symbol}")
                    elif channel == "signals":
                        subscribed_symbols.update(symbols)
                elif action == "unsubscribe":
                    if channel == "prices":
                        for symbol in symbols:
                            await manager.unsubscribe(websocket, f"prices:{symbol}")
                    elif channel == "signals":
                        subscribed_symbols.difference_update(symbols)
            except asyncio.TimeoutError:
                pass
            except Exception:
                pass

            # Stream signals for subscribed symbols
            if subscribed_symbols:
                for symbol in sorted(subscribed_symbols):
                    from app.database.redis_client import get_redis, cache_get, cache_set
                    redis = await get_redis()
                    result = await cache_get(redis, f"ws:signal:{symbol}")
                    if not result:
                        try:
                            from app.services.prediction_engine import get_full_prediction
                            result = await get_full_prediction(symbol)
                            if result and result.get("is_computed", False):
                                from datetime import timedelta
                                await cache_set(redis, f"ws:signal:{symbol}", result, ttl=timedelta(seconds=60))
                        except Exception as e:
                            logger.debug("ws_signals_prediction_error symbol=%s error=%s", symbol, str(e))
                            result = None

                    if not result or not result.get("is_computed", False):
                        continue

                    ens = result.get("ensemble", {})
                    direction = ens.get("direction", "NEUTRAL")
                    signal_score = ens.get("raw_ensemble", 0.0)
                    confidence = ens.get("confidence", 0.5)

                    try:
                        await manager.send_personal(
                            websocket,
                            {
                                "type": "signal",
                                "symbol": symbol,
                                "payload": {
                                    "signal": round(float(signal_score), 4),
                                    "confidence": round(float(confidence), 4),
                                    "direction": direction,
                                },
                                "ts": datetime.now(UTC).isoformat(),
                                "source": "system",
                            },
                        )
                    except Exception:
                        pass
                
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)
"""

if "def ws_stream" not in ws_router:
    ws_router += stream_code
    with open("backend/app/websocket/router.py", "w", encoding="utf-8") as f:
        f.write(ws_router)
print("Patched backend WS")
