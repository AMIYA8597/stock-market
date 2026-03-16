"""
API v1 router configuration.
Includes all endpoint routers with proper middleware and dependencies.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    alerts,
    auth,
    backtesting,
    health,
    market_data,
    portfolio,
    predictions,
    screener,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(market_data.router, prefix="/market-data", tags=["market-data"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
api_router.include_router(backtesting.router, prefix="/backtesting", tags=["backtesting"])
api_router.include_router(screener.router, prefix="/screener", tags=["screener"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(health.router, prefix="/health", tags=["health"])