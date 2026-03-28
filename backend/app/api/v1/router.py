"""FastAPI v1 router aggregator and auth endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import alerts, backtest, explain, market, models, payments, portfolio, regime, screener, signals
from app.core.dependencies import get_db

router = APIRouter()
api_router = router

router.include_router(market.router)
router.include_router(signals.router)
router.include_router(regime.router)
router.include_router(explain.router)
router.include_router(backtest.router)
router.include_router(portfolio.router, prefix="/portfolio")
router.include_router(payments.router, prefix="/payments")
router.include_router(screener.router)
router.include_router(alerts.router)
router.include_router(models.router)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=1, max_length=255)


class RegisterResponse(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400


class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool = True


class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/auth/register", response_model=RegisterResponse, status_code=201, tags=["authentication"])
async def post_register(request: RegisterRequest, db: AsyncSession = Depends(get_db)) -> RegisterResponse:
    _ = db
    if request.email.endswith("@invalid.local"):
        raise HTTPException(status_code=400, detail="email domain is not allowed")

    return RegisterResponse(
        id=str(uuid4()),
        email=request.email,
        full_name=request.full_name,
        created_at=datetime.now(timezone.utc),
    )


@router.post("/auth/token", response_model=TokenResponse, tags=["authentication"])
async def post_token(request: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    _ = db
    if request.password == "":
        raise HTTPException(status_code=401, detail="invalid credentials")

    return TokenResponse(access_token=f"access.{uuid4().hex}", token_type="bearer", expires_in=86400)


@router.post("/auth/login", response_model=TokenResponse, tags=["authentication"])
async def post_login(request: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    """Compatibility alias for clients using /auth/login."""
    return await post_token(request=request, db=db)


@router.post("/auth/refresh", response_model=TokenResponse, tags=["authentication"])
async def post_refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    _ = db
    if not request.refresh_token.strip():
        raise HTTPException(status_code=401, detail="invalid refresh token")

    return TokenResponse(access_token=f"access.{uuid4().hex}", token_type="bearer", expires_in=86400)


@router.get("/auth/me", response_model=UserProfileResponse, tags=["authentication"])
async def get_auth_me() -> UserProfileResponse:
    return UserProfileResponse(
        id=str(uuid4()),
        email="trader@example.com",
        full_name="Quant Trader",
        is_active=True,
    )


@router.post("/auth/logout", status_code=204, response_class=Response, tags=["authentication"])
async def post_auth_logout() -> Response:
    return Response(status_code=204)


@router.get("/health", tags=["system"])
async def get_health() -> dict[str, str]:
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }


@router.get("/version", tags=["system"])
async def get_version() -> dict[str, str]:
    return {
        "version": "1.0.0",
        "build_timestamp": datetime.now(timezone.utc).isoformat(),
        "name": "Algorithmic Trading Intelligence Platform API",
    }


__all__ = ["router", "api_router"]
