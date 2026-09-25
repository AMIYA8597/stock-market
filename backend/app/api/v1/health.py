"""Health check endpoint."""

import logging

from fastapi import APIRouter
from sqlalchemy import text

from app.core.dependencies import get_db, get_redis

logger = logging.getLogger(__name__)

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
    """Returns cached provider status without synchronous network probing."""
    from app.database.redis_client import get_redis_client
    import json
    
    status = {"yfinance": "unknown", "nse": "unknown", "coingecko": "unknown", "fred": "unknown"}
    try:
        redis = await get_redis_client()
        cached = await redis.get("system:provider_health")
        if cached:
            status.update(json.loads(cached))
    except Exception as e:
        logger.warning(f"Could not read provider health from cache: {e}")
        
    return status


@router.get("/ready")
async def readiness_check():
    """Readiness probe with dependency checks for DB and Redis."""
    from fastapi.responses import JSONResponse

    dependencies: dict[str, str] = {"database": "down", "redis": "down"}

    db_ok = False
    redis_ok = False

    from app.core.config import get_settings

    get_settings()

    # 1. Test SQLite connection (primary DB)
    try:
        async for db in get_db():
            await db.execute(text("SELECT 1"))
            db_ok = True
            break
    except Exception as e:
        logger.warning(f"SQLite health check failed: {e}")
        db_ok = False

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
