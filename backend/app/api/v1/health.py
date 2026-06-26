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


@router.get("/debug/trigger-alert-check")
async def debug_trigger_alert_check():
    """Debug endpoint to manually trigger an alert engine cycle.
    Returns the list of alerts that were broadcast.
    """
    from app.services.alert_engine import trigger_one_cycle
    alerts = await trigger_one_cycle()
    return {"alerts_sent": alerts}


@router.get("/ready")
async def readiness_check() -> dict[str, object]:
    """Readiness probe with dependency checks for DB and Redis."""
    dependencies: dict[str, str] = {"database": "down", "redis": "down"}

    db_ok = False
    redis_ok = False

    from app.core.config import get_settings
    settings = get_settings()

    try:
        if settings.MONGODB_URL:
            from app.database.mongodb import get_mongo_db
            mongo_db = get_mongo_db()
            if mongo_db is not None:
                await mongo_db.command("ping")
                db_ok = True
        else:
            async for db in get_db():
                await db.execute(text("SELECT 1"))
                db_ok = True
                break
    except Exception:
        db_ok = False

    try:
        redis = await get_redis()
        redis_ok = bool(await redis.ping())
    except Exception:
        redis_ok = False

    dependencies["database"] = "up" if db_ok else "down"
    dependencies["redis"] = "up" if redis_ok else "down"

    overall = "ready" if all([db_ok, redis_ok]) else "not_ready"
    payload = {
        "status": overall,
        "dependencies": dependencies,
    }
    if overall != "ready":
        raise HTTPException(status_code=503, detail=payload)
    return payload
