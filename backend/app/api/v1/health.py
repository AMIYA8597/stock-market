"""Health check endpoint."""

from sqlalchemy import text

from fastapi import APIRouter, HTTPException

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


@router.get("/ready")
async def readiness_check() -> dict[str, object]:
    """Readiness probe with dependency checks for DB and Redis."""
    dependencies: dict[str, str] = {"database": "down", "redis": "down"}

    db_ok = False
    redis_ok = False

    try:
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
