from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from app.api.v1 import (
    admin,
    alerts,
    auth,
    autotrade,
    backtest,
    blog,
    explain,
    health,
    intelligence,
    journal,
    market,
    models,
    news,
    notifications,
    onboarding,
    organizations,
    paper_trading,
    payments,
    portfolio,
    predictions,
    regime,
    screener,
    users,
    watchlist,
    websocket_url,
)
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()
api_router = router

router.include_router(health.router)
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(organizations.router)
router.include_router(admin.router)
router.include_router(blog.router)
router.include_router(notifications.router)
router.include_router(payments.router)
router.include_router(watchlist.router)


router.include_router(alerts.router)
router.include_router(market.router)
router.include_router(websocket_url.router)

router.include_router(regime.router, dependencies=[Depends(get_current_user)])
router.include_router(news.router)
router.include_router(explain.router, dependencies=[Depends(get_current_user)])
router.include_router(backtest.router)
router.include_router(portfolio.router, prefix="/portfolio")
router.include_router(paper_trading.router)
router.include_router(autotrade.router, dependencies=[Depends(get_current_user)])
router.include_router(screener.router, dependencies=[Depends(get_current_user)])

router.include_router(models.router, dependencies=[Depends(get_current_user)])
router.include_router(intelligence.router, dependencies=[Depends(get_current_user)])
router.include_router(predictions.router, prefix="/predictions", tags=["predictions"], dependencies=[Depends(get_current_user)])
router.include_router(journal.router)
router.include_router(onboarding.router, dependencies=[Depends(get_current_user)])

@router.get("/version", tags=["system"])
async def get_version() -> dict[str, str]:
    return {"version": "2.0.0", "name": "NeuroQuant API"}


__all__ = ["router", "api_router"]
