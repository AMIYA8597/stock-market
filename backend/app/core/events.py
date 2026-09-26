"""Application startup and shutdown event handlers.

Manages lifecycle events for:
- Background task initialization (broadcasters, workers)
- Database connection pooling
- Redis connection pools
- Model cache warmup
- Health check services

These handlers are called by FastAPI lifespan context manager during
application initialization and graceful shutdown.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Any

from sqlalchemy import text

from app.core.config import get_settings
from app.core.logging import get_logger
from app.database.redis_client import _redis_pool_singleton

logger = get_logger(__name__)
settings = get_settings()


async def startup_events() -> dict[str, Any]:
    """Initialize background tasks and services on startup.

    Called during FastAPI application startup. Initializes:
    - Redis connection pool
    - Database connection pool
    - Background tasks (price/signal broadcasters)
    - Model cache warmup
    - Health monitoring

    All errors are logged but non-critical failures don't prevent startup.

    Returns:
        dict[str, Any]: Dictionary of initialized services and tasks.

    Raises:
        RuntimeError: Only if critical service initialization fails.

    Example:
        services = await startup_events()
        # services = {
        #     "redis": Redis,
        #     "background_tasks": [Task, Task, ...],
        # }
    """
    services: dict[str, Any] = {}
    redis_client = None

    logger.info("startup_begin")

    # ─── Widen the default thread pool ─────────────────────────────────────
    # Every synchronous yfinance/NSE/sqlite3 call runs via  # honesty: allow (comment, no real usage)
    # asyncio.to_thread(), which shares Python's default executor
    # (min(32, cpu_count+4) workers). Under realistic concurrent load — e.g.
    # a 20-symbol watchlist each doing a blocking data fetch — that pool
    # saturates and starves unrelated, otherwise-fast requests (even simple
    # DB reads) queued behind it. Raise the ceiling so blocking I/O-bound
    # work doesn't serialize the whole app.
    from concurrent.futures import ThreadPoolExecutor

    asyncio.get_running_loop().set_default_executor(
        ThreadPoolExecutor(max_workers=64, thread_name_prefix="nq-worker")
    )

    try:
        # ─── Initialize Redis Connection Pool ──────────────────────────────
        logger.info("startup_redis_init")
        try:
            redis_client = await _redis_pool_singleton()
            ping_result = await asyncio.wait_for(redis_client.ping(), timeout=2.0)
            logger.info(
                "startup_redis_success",
                ping_result=ping_result,
                redis_url=settings.REDIS_URL,
            )
            services["redis"] = redis_client
        except Exception as e:
            logger.error("startup_redis_failed", error=str(e), exc_info=True)
            logger.warning("Redis is offline. Live WebSocket features will be degraded.")

        # ─── Initialize Database ───────────────────────────────────────────
        logger.info("startup_database_init")
        try:
            from app.core.database import engine

            # Test database connection
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1") if hasattr(conn, "execute") else "SELECT 1")
            logger.info("startup_database_success", database_url=settings.DATABASE_URL)

            # Schema guard is called dynamically by the schema middleware, but we can also do a quick check here.
        except Exception as e:
            logger.error("startup_database_failed", error=str(e), exc_info=True)
            logger.warning("Database is offline. REST services accessing DB will fail.")

        # ─── Initialize Background Tasks ──────────────────────────────────
        background_tasks = []

        logger.info("startup_background_tasks_init")
        try:
            # Price ticker task — continuous polling/broadcast loop. Its CPU-
            # bound work (batch quote processing every cycle) competes with
            # this single-process server's event loop for the same requests
            # users are waiting on, measurably slowing down foreground
            # requests (login went from ~0.2s in isolation to ~3s under this
            # load, confirmed via direct timing). Real value in production
            # (separate worker process there); not worth the latency hit in
            # local dev.
            if settings.is_production:
                try:
                    from app.websocket.price_ticker import run_price_ticker

                    if redis_client:
                        ticker_task = asyncio.create_task(
                            run_price_ticker(redis_client),
                            name="price_ticker",
                        )
                        background_tasks.append(ticker_task)
                        logger.info("startup_price_ticker_created")
                except Exception as e:
                    logger.error(f"Failed to start price ticker task: {e}")
            else:
                logger.info("startup_price_ticker_skipped_dev_mode")

            # Note: alert polling is handled entirely by the Alert Evaluator
            # below (app.workers.alert_evaluator), which queries Alert/
            # AlertEvent against the real schema. A second, parallel
            # "alert_engine.py"-based polling loop used to run here too; it
            # depended on a app.services.signal_engine module that doesn't
            # exist in this codebase and has been removed as dead/duplicate
            # code rather than fixed, since alert_evaluator already covers
            # this responsibility correctly.

            # Initialize Background Market Scheduler removed per Stage 1 requirements
            logger.info("startup_market_scheduler_skipped")

            # Initialize Alert Evaluator — same event-loop contention
            # reasoning as price_ticker above; production-only.
            if settings.is_production:
                try:
                    from app.workers.alert_evaluator import evaluator as alert_evaluator

                    await alert_evaluator.start()
                    if alert_evaluator._task:
                        background_tasks.append(alert_evaluator._task)
                    logger.info("startup_alert_evaluator_started")
                except Exception as err:
                    logger.error(f"Failed to start alert evaluator: {err}")
            else:
                logger.info("startup_alert_evaluator_skipped_dev_mode")

            if background_tasks:
                services["background_tasks"] = background_tasks
                logger.info(
                    "startup_background_tasks_success",
                    task_count=len(background_tasks),
                )

        except Exception as e:
            logger.error("startup_background_tasks_failed", error=str(e), exc_info=True)

        # ─── Model Cache Warmup ───────────────────────────────────────────
        logger.info("startup_model_cache_init")
        try:
            # Placeholder: Load and cache ML models if inference service exists
            if redis_client:
                # Example: Warm up common model inference calls
                cache_warmed = await redis_client.get("model_cache_warmed")
                if not cache_warmed:
                    logger.info("startup_model_cache_warming")
                    await redis_client.setex(
                        "model_cache_warmed",
                        3600,
                        "true",
                    )
                    logger.info("startup_model_cache_warmed")
        except Exception as e:
            logger.warning("startup_model_cache_failed", error=str(e))

        # ─── Health Check Service ────────────────────────────────────────
        logger.info("startup_health_check_init")
        try:
            if redis_client:
                await redis_client.setex(
                    "app_startup_time",
                    86400,
                    str(asyncio.get_event_loop().time()),
                )
            logger.info("startup_health_check_success")
        except Exception as e:
            logger.warning("startup_health_check_failed", error=str(e))

        logger.info("startup_complete", services_initialized=list(services.keys()))
        from app.core.websocket_manager import ws_manager
        await ws_manager.startup()
        return services

    except Exception as e:
        logger.critical("startup_failed", error=str(e), exc_info=True)
        raise RuntimeError(f"Application startup failed: {e}") from e


async def shutdown_events(services: dict[str, Any]) -> None:
    """Gracefully shutdown services and cancel background tasks.

    Called during FastAPI application shutdown. Cleanly closes:
    - Background tasks (broadcasters, workers)
    - Database connection pool
    - Redis connection pool

    Uses asyncio.CancelledError suppression to ensure all cleanup occurs
    even if individual tasks fail.

    Args:
        services: Dictionary of initialized services from startup_events().

    Returns:
        None

    Raises:
        None: All exceptions are logged but suppressed to ensure cleanup completes.

    Example:
        services = await startup_events()
        # ... application runs ...
        await shutdown_events(services)
    """
    logger.info("shutdown_begin")

    try:
        # ─── Cancel Background Tasks ──────────────────────────────────────
        background_tasks = services.get("background_tasks", [])
        if background_tasks:
            logger.info("shutdown_background_tasks", task_count=len(background_tasks))
            for task in background_tasks:
                task.cancel()

            # Wait for cancellation to complete
            for task in background_tasks:
                with suppress(asyncio.CancelledError):
                    await task

            logger.info("shutdown_background_tasks_complete")

        # ─── Close Redis Connection ────────────────────────────────────────
        redis_client = services.get("redis")
        if redis_client:
            logger.info("shutdown_redis")
            try:
                await redis_client.close()
                logger.info("shutdown_redis_complete")
            except Exception as e:
                logger.warning("shutdown_redis_error", error=str(e))

        # ─── Close Database Connections ───────────────────────────────────
        # Background Scheduler removed per Stage 1 requirements

        logger.info("shutdown_database")
        try:
            from app.core.database import engine

            await engine.dispose()
            logger.info("shutdown_database_complete")
        except Exception as e:
            logger.warning("shutdown_database_error", error=str(e))

        logger.info("shutdown_complete")

    except Exception as e:
        logger.error("shutdown_error", error=str(e), exc_info=True)


# ─── Helper: Lifespan Context Manager ──────────────────────────────────
async def lifespan(app: Any):
    """FastAPI lifespan context manager for startup/shutdown.

    Usage in main.py:
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def lifespan(app):
            # Startup
            services = await startup_events()
            yield
            # Shutdown
            await shutdown_events(services)

        app = FastAPI(lifespan=lifespan)

    Args:
        app: FastAPI application instance.

    Yields:
        None

    Raises:
        None: Exceptions from startup/shutdown are logged and handled.
    """
    services = {}

    try:
        services = await startup_events()
    except Exception as e:
        logger.critical("lifespan_startup_failed", error=str(e), exc_info=True)
        raise

    yield

    try:
        await shutdown_events(services)
    except Exception as e:
        logger.critical("lifespan_shutdown_failed", error=str(e), exc_info=True)
