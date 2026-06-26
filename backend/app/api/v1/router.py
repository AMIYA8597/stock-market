from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    alerts,
    auth,
    backtest,
    blog,
    explain,
    health,
    market,
    market_data,
    models,
    notifications,
    payments,
    portfolio,
    regime,
    screener,
    signals,
    users,
    predictions,
    journal,
    paper_trading,
    trading,
)

router = APIRouter()
api_router = router

router.include_router(health.router)
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(admin.router)
router.include_router(blog.router)
router.include_router(notifications.router)
router.include_router(payments.router)

router.include_router(market_data.router, prefix="/global", tags=["market-data"])
router.include_router(market.router)
router.include_router(signals.router)
router.include_router(regime.router)
router.include_router(explain.router)
router.include_router(backtest.router)
router.include_router(portfolio.router, prefix="/portfolio")
router.include_router(paper_trading.router)
router.include_router(trading.router)
router.include_router(screener.router)
router.include_router(alerts.router)
router.include_router(models.router)
router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
router.include_router(journal.router)


@router.get("/version", tags=["system"])
async def get_version() -> dict[str, str]:
    return {
        "version": "2.0.0",
        "name": "NeuroQuant API",
    }


@router.post("/debug/trigger-alert-check", tags=["debug"])
async def trigger_alert_check():
    from app.services.alert_engine import check_and_fire_alerts
    WATCHLIST_SYMBOLS = [
        "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "HINDUNILVR.NS",
        "ICICIBANK.NS", "KOTAKBANK.NS", "SBIN.NS", "WIPRO.NS", "BAJFINANCE.NS",
        "NIFTY50.NS", "^NSEI"
    ]
    from app.websocket.connection_manager import get_connection_manager
    manager = get_connection_manager()
    alerts = await check_and_fire_alerts(WATCHLIST_SYMBOLS, manager)
    return {"status": "ok", "alerts_fired_count": len(alerts), "alerts": alerts}


__all__ = ["router", "api_router"]
