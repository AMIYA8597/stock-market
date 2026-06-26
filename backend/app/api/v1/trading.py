# backend/app/api/v1/trading.py
"""API endpoints for live terminal operations, safety gates, and OAuth callbacks."""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_current_user_or_none, get_db
from app.services.upstox_service import UpstoxService
from app.services.broker_adapter import BrokerAdapter

logger = logging.getLogger(__name__)

router = APIRouter()


class ModeUpdateSchema(BaseModel):
    mode: str = Field(..., description="Target trading mode: 'PAPER' or 'LIVE'")


class OrderSubmitSchema(BaseModel):
    symbol: str = Field(..., description="Stock or index trading symbol, e.g., 'RELIANCE'")
    side: str = Field(..., description="Transaction direction: 'BUY' or 'SELL'")
    quantity: float = Field(..., description="Number of units to trade")
    order_type: str = Field(..., description="Execution type: 'MARKET' or 'LIMIT'")
    limit_price: Optional[float] = Field(None, description="Price boundary for LIMIT orders")
    product: Optional[str] = Field("I", description="Product selection: 'I' (Intraday) or 'D' (Delivery)")


@router.get("/trading/mode")
async def get_trading_mode(current_user: Any = Depends(get_current_user_or_none)):
    """Returns the current trading session mode and connectivity state."""
    profile_summary = None
    if UpstoxService.USER_PROFILE:
        profile_summary = {
            "name": UpstoxService.USER_PROFILE.get("user_name"),
            "email": UpstoxService.USER_PROFILE.get("email"),
            "broker": "Upstox"
        }
        
    return {
        "trading_mode": UpstoxService.TRADING_MODE,
        "connection_status": UpstoxService.CONNECTION_STATUS,
        "authenticated": UpstoxService.ACCESS_TOKEN is not None,
        "profile": profile_summary
    }


@router.post("/trading/mode")
async def set_trading_mode(
    payload: ModeUpdateSchema,
    current_user: Any = Depends(get_current_user_or_none)
):
    """Toggles trading session mode between PAPER and LIVE."""
    target_mode = payload.mode.upper().strip()
    
    if target_mode not in ("PAPER", "LIVE"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mode. Must be 'PAPER' or 'LIVE'."
        )
        
    if target_mode == "LIVE":
        if not UpstoxService.ACCESS_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication Required: Upstox access token is missing or expired. Authenticate first."
            )
            
    old_mode = UpstoxService.TRADING_MODE
    UpstoxService.TRADING_MODE = target_mode
    user_id = current_user.get("sub") if (current_user and isinstance(current_user, dict)) else "guest-user"
    UpstoxService.log_audit(f"TRADING MODE SWITCHED: {old_mode} -> {target_mode} by user={user_id}")
    
    return {
        "status": "success",
        "trading_mode": UpstoxService.TRADING_MODE,
        "message": f"Trading mode successfully updated to {target_mode}."
    }


@router.post("/trading/order")
async def submit_order(
    order: OrderSubmitSchema,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user_or_none)
):
    """Places a simulated or real trade order depending on active trading mode."""
    try:
        res = await BrokerAdapter.place_order(
            db=db,
            user_id=str(current_user.get("sub") if (current_user and isinstance(current_user, dict)) else "guest-user"),
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            order_type=order.order_type,
            limit_price=order.limit_price,
            product=order.product or "I"
        )
        return res
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as e:
        logger.error(f"Order submission error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order submission failed: {str(e)}"
        )


@router.post("/trading/kill-switch")
async def emergency_kill_switch(
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user_or_none)
):
    """Emergency Kill Switch: reverts trading mode to PAPER and cancels open orders."""
    user_id = current_user.get("sub") if (current_user and isinstance(current_user, dict)) else "guest-user"
    old_mode = UpstoxService.TRADING_MODE
    UpstoxService.TRADING_MODE = "PAPER"
    
    UpstoxService.log_audit(
        f"[KILL SWITCH ACTIVATED] Mode forced to PAPER by user={user_id} (Previous: {old_mode})"
    )
    
    cancel_info = []
    
    # 1. Cancel open simulated limit orders from database
    try:
        from app.models.paper_trading import PaperOrder
        from sqlalchemy import update
        
        # Mark all pending paper orders as CANCELLED
        stmt = (
            update(PaperOrder)
            .where(PaperOrder.user_id == str(user_id), PaperOrder.status == "PENDING")
            .values(status="CANCELLED")
        )
        res = await db.execute(stmt)
        await db.commit()
        
        cancel_info.append(f"Cancelled {res.rowcount} pending paper orders.")
    except Exception as e:
        logger.error(f"Failed to cancel pending paper orders during kill switch: {e}")
        cancel_info.append(f"Paper orders cancel error: {str(e)}")

    # 2. Revert Upstox WebSocket Streamer subscription if live
    try:
        await UpstoxService.stop_websocket_feed()
        cancel_info.append("Stopped live Upstox WebSocket ticker feed.")
    except Exception as e:
        logger.error(f"Failed to disconnect Upstox feed during kill switch: {e}")
        cancel_info.append(f"Upstox WS close error: {str(e)}")
        
    return {
        "status": "success",
        "trading_mode": "PAPER",
        "message": "Emergency Kill Switch Activated: Mode forced to PAPER.",
        "operations": cancel_info
    }


@router.get("/trading/audit-log")
async def get_audit_log(
    limit: int = Query(50, ge=1, le=200),
    current_user: Any = Depends(get_current_user_or_none)
):
    """Reads the trailing rows of the audit log file d:\\work\\stock-market\\backend\\logs\\trading_audit.log."""
    backend_root = Path(__file__).resolve().parent.parent.parent.parent
    audit_file = backend_root / "logs" / "trading_audit.log"
    
    if not audit_file.exists():
        return {"logs": []}
        
    try:
        # Read trailing lines
        with open(audit_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        trail = [line.strip() for line in lines[-limit:]]
        return {"logs": trail}
    except Exception as e:
        logger.error(f"Error reading audit log: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not read audit logs: {str(e)}"
        )


# ─── Upstox OAuth Authentication Endpoints ─────────────────────────────────

@router.get("/auth/upstox/login-url")
async def get_upstox_login_url(current_user: Any = Depends(get_current_user_or_none)):
    """Exposes the authorization dialog link for Upstox developer integrations."""
    try:
        login_url = UpstoxService.get_login_url()
        return {"login_url": login_url}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/auth/upstox/callback")
async def upstox_oauth_callback(
    code: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None
):
    """OAuth redirect handler callback from Upstox API code consent dialog."""
    settings = get_settings()
    frontend_url = settings.NEXTAUTH_URL or "http://localhost:3000"
    
    if error:
        logger.error(f"Upstox OAuth error callback: {error} - {error_description}")
        return RedirectResponse(url=f"{frontend_url}/?upstox_auth=failed&error={error}")
        
    if not code:
        logger.error("Upstox callback endpoint hit without authorization code.")
        return RedirectResponse(url=f"{frontend_url}/?upstox_auth=failed&error=no_code")
        
    try:
        # exchange code for token
        await UpstoxService.exchange_code_for_token(code)
        return RedirectResponse(url=f"{frontend_url}/?upstox_auth=success")
    except Exception as ex:
        logger.error(f"Failed to authenticate code with Upstox: {ex}")
        return RedirectResponse(url=f"{frontend_url}/?upstox_auth=failed&error={str(ex)}")


@router.get("/auth/upstox/status")
async def get_upstox_auth_status(current_user: Any = Depends(get_current_user_or_none)):
    """Returns profile and validity details for the active Upstox authentication."""
    profile_summary = None
    if UpstoxService.USER_PROFILE:
        profile_summary = {
            "name": UpstoxService.USER_PROFILE.get("user_name"),
            "email": UpstoxService.USER_PROFILE.get("email"),
            "client_id": UpstoxService.USER_PROFILE.get("client_id")
        }
        
    return {
        "authenticated": UpstoxService.ACCESS_TOKEN is not None,
        "profile": profile_summary,
        "connection_status": UpstoxService.CONNECTION_STATUS
    }
