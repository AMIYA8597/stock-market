"""Trading mode and audit log endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.dependencies import get_current_user

router = APIRouter(prefix="/trading", tags=["trading"])


class TradingModeResponse(BaseModel):
    trading_mode: str
    is_live: bool


class SetModeRequest(BaseModel):
    mode: str


@router.get("/mode")
async def get_trading_mode(
    current_user: dict = Depends(get_current_user),
) -> TradingModeResponse:
    return TradingModeResponse(trading_mode="PAPER", is_live=False)


@router.post("/mode")
async def set_trading_mode(
    request: SetModeRequest,
    current_user: dict = Depends(get_current_user),
) -> TradingModeResponse:
    mode = request.mode.upper()
    is_live = mode == "LIVE"
    return TradingModeResponse(trading_mode=mode, is_live=is_live)


@router.get("/audit-log")
async def get_audit_log(
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    return {"entries": [], "total": 0}
