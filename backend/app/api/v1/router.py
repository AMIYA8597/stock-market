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
    market_data,
    models,
    notifications,
    payments,
    portfolio,
    regime,
    screener,
    signals,
    users,
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

router.include_router(market_data.router, prefix="/market", tags=["market"])
router.include_router(signals.router)
router.include_router(regime.router)
router.include_router(explain.router)
router.include_router(backtest.router)
router.include_router(portfolio.router, prefix="/portfolio")
router.include_router(screener.router)
router.include_router(alerts.router)
router.include_router(models.router)


@router.get("/version", tags=["system"])
async def get_version() -> dict[str, str]:
    return {
        "version": "2.0.0",
        "name": "NeuroQuant API",
    }


__all__ = ["router", "api_router"]
