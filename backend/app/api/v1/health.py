"""Health check endpoint."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.core.dependencies import get_db, get_redis

router = APIRouter()


@router.get("/health")
async def health_check():
    """Application health check — returns service status."""
    return {
        "status": "healthy",
        "service": "quantedge-api",
        "version": "0.1.0",
    }


@router.get("/health/live-data")
async def health_live_data():
    """Pings external data sources to check reachability."""
    import httpx
    from app.core.config import get_settings
    settings = get_settings()
    
    status = {
        "yfinance": "down",
        "nse": "down",
        "coingecko": "down",
        "fred": "down"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    async with httpx.AsyncClient(timeout=5) as client:
        # 1. Ping yfinance
        try:
            resp = await client.get("https://query1.finance.yahoo.com/v8/finance/chart/AAPL?interval=1d&range=1d", headers=headers)
            if resp.status_code == 200:
                status["yfinance"] = "up"
        except Exception:
            pass

        # 2. Ping NSE
        try:
            # First load home page to get session/cookies
            resp1 = await client.get("https://www.nseindia.com", headers=headers)
            if resp1.status_code == 200:
                resp2 = await client.get("https://www.nseindia.com/api/historical/cm/equity?symbol=RELIANCE&series=[%22EQ%22]", headers=headers, cookies=resp1.cookies)
                if resp2.status_code == 200:
                    status["nse"] = "up"
                else:
                    status["nse"] = "up"
        except Exception:
            pass

        # 3. Ping CoinGecko
        try:
            cg_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
            cg_headers = {"accept": "application/json"}
            if settings.COINGECKO_API_KEY:
                cg_headers["x-cg-pro-api-key"] = settings.COINGECKO_API_KEY
            resp = await client.get(cg_url, headers=cg_headers)
            if resp.status_code == 200:
                status["coingecko"] = "up"
        except Exception:
            pass

        # 4. Ping FRED
        try:
            if settings.FRED_API_KEY:
                fred_url = f"https://api.stlouisfed.org/fred/series?series_id=GDPC1&api_key={settings.FRED_API_KEY}&file_type=json"
                resp = await client.get(fred_url)
                if resp.status_code == 200:
                    status["fred"] = "up"
            else:
                resp = await client.get("https://api.stlouisfed.org")
                if resp.status_code == 200 or resp.status_code == 403:
                    status["fred"] = "up"
        except Exception:
            pass

    return status


@router.get("/debug/trigger-alert-check")
async def debug_trigger_alert_check():
    """Debug endpoint to manually trigger an alert engine cycle.
    Returns the list of alerts that were broadcast.
    """
    from app.services.alert_engine import trigger_one_cycle
    alerts = await trigger_one_cycle()
    return {"alerts_sent": alerts}


@router.get("/ready")
async def readiness_check():
    """Readiness probe with dependency checks for DB and Redis."""
    from fastapi.responses import JSONResponse
    dependencies: dict[str, str] = {"database": "down", "redis": "down"}

    db_ok = False
    redis_ok = False

    from app.core.config import get_settings
    settings = get_settings()

    # 1. Test SQLite connection (primary DB)
    try:
        async for db in get_db():
            await db.execute(text("SELECT 1"))
            db_ok = True
            break
    except Exception as e:
        logger.warning(f"SQLite health check failed: {e}")
        db_ok = False

    # 2. Test MongoDB (optional but checked if configured)
    mongo_ok = True
    if settings.MONGODB_URL:
        try:
            from app.database.mongodb import get_mongo_db
            mongo_db = get_mongo_db()
            if mongo_db is not None:
                await mongo_db.command("ping")
            else:
                mongo_ok = False
        except Exception as e:
            logger.warning(f"MongoDB health check failed: {e}")
            mongo_ok = False

    # 3. Test Redis connection (optional)
    try:
        redis = await get_redis()
        redis_ok = bool(await redis.ping())
    except Exception:
        redis_ok = False

    dependencies["database"] = "up" if db_ok else "down"
    dependencies["redis"] = "up" if redis_ok else "down"

    # Overall is ready if primary SQLite is UP
    overall = "ready" if db_ok else "not_ready"
    payload = {
        "status": overall,
        "dependencies": dependencies,
    }
    if overall != "ready":
        return JSONResponse(status_code=503, content=payload)
    return payload

