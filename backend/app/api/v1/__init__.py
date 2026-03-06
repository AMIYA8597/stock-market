"""API v1 — all routers aggregated here."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.market_data import router as market_router
from app.api.v1.predictions import router as predictions_router
from app.api.v1.portfolio import router as portfolio_router
from app.api.v1.backtesting import router as backtest_router
from app.api.v1.screener import router as screener_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.health import router as health_router

api_router = APIRouter()

api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(market_router, prefix="/market", tags=["market data"])
api_router.include_router(predictions_router, prefix="/predictions", tags=["predictions"])
api_router.include_router(portfolio_router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(backtest_router, prefix="/backtest", tags=["backtesting"])
api_router.include_router(screener_router, prefix="/screener", tags=["screener"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["alerts"])
