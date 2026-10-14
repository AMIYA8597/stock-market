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
    import json

    from app.database.redis_client import get_redis_client

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
        from app.database.redis_client import InMemoryCache

        if get_settings().is_production and isinstance(redis, InMemoryCache):
            redis_ok = False
    except Exception:
        redis_ok = False

    dependencies["database"] = "up" if db_ok else "down"
    dependencies["redis"] = "up" if redis_ok else "down"

    # Production requires a shared Redis instance for rate limiting, pub/sub,
    # and live-data fan-out. An in-memory fallback is not safe across Cloud Run
    # instances and must not be reported as ready.
    overall = "ready" if db_ok and (redis_ok or not get_settings().is_production) else "not_ready"
    payload = {
        "status": overall,
        "dependencies": dependencies,
    }
    if overall != "ready":
        return JSONResponse(status_code=503, content=payload)
    return payload


@router.get("/health/system-audit")
async def system_audit():
    """Comprehensive system status — honest about what works and what doesn't."""
    from pathlib import Path

    from app.core.config import get_settings
    from app.database.redis_client import get_redis_client

    settings = get_settings()
    MODEL_DIR = Path(__file__).parent.parent.parent / "data" / "models"
    ARTIFACT_DIR = Path(__file__).parent.parent.parent / "data" / "artifacts"

    redis_type = "unknown"
    try:
        redis = await get_redis_client()
        redis_type = type(redis).__name__
    except Exception:
        pass

    pkl_files = list(MODEL_DIR.glob("**/*.pkl")) + list(ARTIFACT_DIR.glob("**/*.pkl"))

    upstox_configured = bool(
        getattr(settings, "UPSTOX_ENABLED", False)
        and getattr(settings, "UPSTOX_ANALYTICS_TOKEN", None)
    )

    db_instruments = 0
    upstox_aliases = 0
    try:
        from sqlalchemy import func, select

        from app.database.connection import async_session_factory
        from app.models.market import Instrument, InstrumentAlias

        async with async_session_factory() as db:
            db_instruments = (await db.execute(select(func.count(Instrument.id)))).scalar() or 0
            upstox_aliases = (
                await db.execute(
                    select(func.count(InstrumentAlias.id)).where(
                        InstrumentAlias.provider == "upstox"
                    )
                )
            ).scalar() or 0
    except Exception:
        pass

    return {
        "data_providers": {
            "yfinance": {"status": "active", "role": "fallback"},
            "upstox": {
                "status": "configured" if upstox_configured else "disabled",
                "token_set": bool(getattr(settings, "UPSTOX_ANALYTICS_TOKEN", None)),
                "instruments_synced": upstox_aliases > 0,
                "alias_count": upstox_aliases,
            },
        },
        "database": {
            "instruments": db_instruments,
            "upstox_aliases": upstox_aliases,
        },
        "cache": {
            "type": redis_type,
            "is_real_redis": redis_type not in ("InMemoryCache", "FakeRedis"),
        },
        "ml_models": {
            "pkl_artifacts_on_disk": len(pkl_files),
            "pkl_files": [f.name for f in pkl_files],
            "hmm_garch_json": len(list(MODEL_DIR.glob("hmm_garch/*.json"))),
            "training_pipeline_exists": True,
            "training_ever_run": len(pkl_files) > 0,
        },
    }
