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

        # ─── Initialize Database ──────────────────────────────────────────
        logger.info("startup_database_init")
        try:
            from app.core.database import engine, init_db

            # Test database connection
            async with engine.begin() as conn:
                await conn.execute(
                    text("SELECT 1")
                    if hasattr(conn, "execute")
                    else "SELECT 1"
                )
            logger.info("startup_database_success", database_url=settings.DATABASE_URL)
            
            # Automatically create tables if not exists
            logger.info("startup_database_schema_sync")
            await init_db()
        except Exception as e:
            logger.error("startup_database_failed", error=str(e), exc_info=True)
            logger.warning("Database is offline. REST services accessing DB will fail.")

        # ─── Initialize Background Tasks ──────────────────────────────────
        background_tasks = []

        logger.info("startup_background_tasks_init")
        try:


            # Price ticker task
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

            # Example: Signal broadcaster (if websocket module exists)
            try:
                from app.websocket.signal_broadcaster import run_signal_broadcaster

                if redis_client:
                    signal_task = asyncio.create_task(
                        run_signal_broadcaster(redis_client),
                        name="signal_broadcaster",
                    )
                    background_tasks.append(signal_task)
                    logger.info("startup_signal_broadcaster_created")
            except (ImportError, AttributeError):
                logger.debug("signal_broadcaster_module_not_found")

            # Alert polling loop task
            try:
                WATCHLIST_SYMBOLS = [
                    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "HINDUNILVR.NS",
                    "ICICIBANK.NS", "KOTAKBANK.NS", "SBIN.NS", "WIPRO.NS", "BAJFINANCE.NS",
                    "^NSEI"
                ]
                
                async def alert_polling_loop():
                    # Sleep slightly on startup to let server initialize
                    await asyncio.sleep(5)
                    while True:
                        try:
                            from app.services.alert_engine import check_and_fire_alerts
                            from app.websocket.connection_manager import get_connection_manager
                            manager = get_connection_manager()
                            await check_and_fire_alerts(WATCHLIST_SYMBOLS, manager)
                        except Exception as loop_err:
                            logger.warning(f"Alert polling error: {loop_err}")
                        await asyncio.sleep(300)

                alert_task = asyncio.create_task(alert_polling_loop(), name="alert_polling_loop")
                background_tasks.append(alert_task)
                logger.info("startup_alert_polling_loop_created")
            except Exception as e:
                logger.error(f"Failed to start alert polling loop background task: {e}")

            # Initialize Upstox Integration
            try:
                from app.services.upstox_service import UpstoxService
                await UpstoxService.init_service()
                logger.info("startup_upstox_service_initialized")
            except Exception as up_err:
                logger.error(f"Failed to initialize Upstox service: {up_err}")

            # Initialize Background Market Scheduler
            try:
                from app.services.data_ingestion.scheduler import market_scheduler
                market_scheduler.start()
                logger.info("startup_market_scheduler_started")
            except Exception as sched_err:
                logger.error(f"Failed to start market scheduler: {sched_err}")

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
        # Close Background Scheduler
        try:
            from app.services.data_ingestion.scheduler import market_scheduler
            market_scheduler.shutdown()
            logger.info("shutdown_market_scheduler_complete")
        except Exception as e:
            logger.warning("shutdown_market_scheduler_error", error=str(e))

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

