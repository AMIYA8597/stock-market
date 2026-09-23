import re

with open('backend/app/websocket/router.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Update ws_prices
code = code.replace(
    'async def ws_prices(websocket: WebSocket):',
    'async def ws_prices(websocket: WebSocket, token: str = ""):\n    from app.websocket.ws_auth import authenticate_ws\n    user_id = await authenticate_ws(websocket, token)\n    if not user_id: return'
)

# 2. Update ws_signals
code = code.replace(
    'async def ws_signals(websocket: WebSocket):',
    'async def ws_signals(websocket: WebSocket, token: str = ""):\n    from app.websocket.ws_auth import authenticate_ws\n    user_id = await authenticate_ws(websocket, token)\n    if not user_id: return'
)

# 3. Update ws_alerts
code = code.replace(
    'async def ws_alerts(websocket: WebSocket):',
    'async def ws_alerts(websocket: WebSocket, token: str = ""):\n    from app.websocket.ws_auth import authenticate_ws\n    user_id = await authenticate_ws(websocket, token)\n    if not user_id: return'
)
code = code.replace(
    'await manager.subscribe(websocket, "signals:alerts")',
    'await manager.subscribe(websocket, f"alerts:{user_id}")'
)

# 4. Fix backtest_progress
code = re.sub(
    r'    try:\n        token_data = decode_token\(token\)\n        user_id_str = token_data.get\("sub"\)\n        if not user_id_str:\n            await websocket.close\(code=1008\)\n            return\n    except Exception:\n        await websocket.close\(code=1008\)\n        return',
    '    from app.websocket.ws_auth import authenticate_ws\n    user_id_str = await authenticate_ws(websocket, token)\n    if not user_id_str:\n        return',
    code
)

# Also remove decode_token import
code = re.sub(
    r'from app\.core\.security import decode_token\n',
    '',
    code
)

with open('backend/app/websocket/router.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('Patched router.py')
