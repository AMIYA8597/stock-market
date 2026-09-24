import re
with open('app/websocket/router.py', 'r') as f:
    content = f.read()

content = re.sub(r'# In-process signal cache.*?\n_signal_cache.*?\{\}\n_SIGNAL_CACHE_TTL = 60\.0  # seconds', '', content, flags=re.DOTALL)

old_cache_logic = """                # Check in-process cache
                cached = _signal_cache.get(symbol)
                if cached and (now_ts - cached[1]) < _SIGNAL_CACHE_TTL:
                    result = cached[0]
                else:
                    try:
                        result = await get_full_prediction(symbol)
                        if result and result.get("is_computed", False):
                            _signal_cache[symbol] = (result, now_ts)
                    except Exception as e:
                        logger.debug(
                            "ws_signals_prediction_error symbol=%s error=%s", symbol, str(e)
                        )
                        result = None"""

new_cache_logic = """                from app.database.redis_client import get_redis, cache_get, cache_set
                redis = await get_redis()
                result = await cache_get(redis, f"ws:signal:{symbol}")
                if not result:
                    try:
                        result = await get_full_prediction(symbol)
                        if result and result.get("is_computed", False):
                            from datetime import timedelta
                            await cache_set(redis, f"ws:signal:{symbol}", result, ttl=timedelta(seconds=60))
                    except Exception as e:
                        logger.debug("ws_signals_prediction_error symbol=%s error=%s", symbol, str(e))
                        result = None"""

content = content.replace(old_cache_logic, new_cache_logic)

with open('app/websocket/router.py', 'w') as f:
    f.write(content)
