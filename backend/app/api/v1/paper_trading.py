"""FastAPI Router for Paper Trading endpoints."""

from __future__ import annotations

from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_or_none, get_db
from app.services.paper_trading import PaperTradingService
from app.schemas.errors import ErrorCode, ErrorResponse

router = APIRouter(prefix="/paper-trade", tags=["paper-trading"])


class OrderRequest(BaseModel):
    symbol: str = Field(..., description="Ticker symbol (e.g. RELIANCE.NS, BTC-USD)")
    side: Literal["BUY", "SELL"] = Field(..., description="Order side")
    quantity: float = Field(..., gt=0, description="Order quantity")
    order_type: Literal["MARKET", "LIMIT"] = Field(..., description="Order type")
    limit_price: float | None = Field(None, description="Limit price, required for LIMIT orders")
    signal_relation: Literal["AGREEMENT", "AGAINST", "INDEPENDENT", "AUTO"] | None = Field("AUTO", description="Relationship of order to active signal. Auto-detected by default.")


@router.post("/order", summary="Submit a paper trading order")
async def submit_order(
    request: OrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_or_none),
):
    user_id = current_user.get("sub") if current_user else "test-user-id"
    try:
        order = await PaperTradingService.place_order(
            db=db,
            user_id=user_id,
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            order_type=request.order_type,
            limit_price=request.limit_price,
            signal_relation=request.signal_relation,
        )
        return {
            "success": True,
            "order": {
                "id": str(order.id),
                "symbol": order.symbol,
                "side": order.side,
                "quantity": float(order.quantity),
                "price": float(order.price),
                "order_type": order.order_type,
                "status": order.status,
                "net_amount": float(order.net_amount),
                "signal_relation": order.signal_relation,
                "timestamp": order.timestamp.isoformat(),
            }
        }
    except ValueError as val_err:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse.create(
                code=ErrorCode.VALIDATION_ERROR,
                message=str(val_err),
            ).dict()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Order execution failed: {str(exc)}",
            ).dict()
        )


@router.get("/positions", summary="Get open paper trading positions")
async def get_positions(
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_or_none),
):
    user_id = current_user.get("sub") if current_user else "test-user-id"
    try:
        positions = await PaperTradingService.get_positions(db, user_id)
        return positions
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Failed to fetch positions: {str(exc)}",
            ).dict()
        )


@router.get("/history", summary="Get paper trading order log")
async def get_history(
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_or_none),
):
    user_id = current_user.get("sub") if current_user else "test-user-id"
    try:
        history = await PaperTradingService.get_history(db, user_id)
        return history
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Failed to fetch order history: {str(exc)}",
            ).dict()
        )


@router.get("/pnl", summary="Get paper trading wallet stats and P&L")
async def get_pnl(
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_or_none),
):
    user_id = current_user.get("sub") if current_user else "test-user-id"
    try:
        pnl_stats = await PaperTradingService.get_pnl(db, user_id)
        return pnl_stats
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Failed to fetch P&L stats: {str(exc)}",
            ).dict()
        )


@router.post("/reset", summary="Reset paper trading wallet")
async def reset_wallet(
    db: AsyncSession = Depends(get_db),
    current_user: dict | None = Depends(get_current_user_or_none),
):
    user_id = current_user.get("sub") if current_user else "test-user-id"
    try:
        pnl_stats = await PaperTradingService.reset_wallet(db, user_id)
        return {
            "success": True,
            "message": "Paper trading wallet and positions reset successfully.",
            "pnl": pnl_stats,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse.create(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Failed to reset wallet: {str(exc)}",
            ).dict()
        )
