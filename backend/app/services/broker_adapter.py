# backend/app/services/broker_adapter.py
"""Broker Adapter Service.

Gated execution router that implements the safety gate (Section 6).
Handles paper trading execution vs real order execution via Upstox REST API.
Enforces per-order risk cap and audits all transactions.
"""

from __future__ import annotations

import logging
import httpx
from decimal import Decimal
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.services.upstox_service import UpstoxService
from app.services.paper_trading import PaperTradingService
from app.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class BrokerAdapter:
    @staticmethod
    async def place_order(
        db: AsyncSession,
        user_id: str,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str,
        limit_price: float | None = None,
        product: str = "I"  # Default "I" for Intraday, "D" for Delivery
    ) -> Dict[str, Any]:
        """Unified gateway for executing buy/sell orders.
        
        Checks current TRADING_MODE and routes to either simulated Paper Trading
        or real execution via Upstox REST API with strict safety gate checks.
        """
        symbol = symbol.upper().strip()
        side = side.upper().strip()
        order_type = order_type.upper().strip()
        product = product.upper().strip()
        
        mode = UpstoxService.TRADING_MODE
        
        if mode == "PAPER":
            # Execute simulated transaction in Paper trading database
            UpstoxService.log_audit(
                f"[PAPER ORDER SUBMITTED] User={user_id} Symbol={symbol} Side={side} Qty={quantity} Type={order_type} Limit={limit_price}"
            )
            try:
                order = await PaperTradingService.place_order(
                    db=db,
                    user_id=user_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    order_type=order_type,
                    limit_price=limit_price,
                    signal_relation="AUTO"
                )
                
                # Fetch order detail
                order_id = str(order.id) if hasattr(order, "id") else "MOCK_PAPER_ID"
                status = str(order.status) if hasattr(order, "status") else "FILLED"
                price_filled = float(order.price) if hasattr(order, "price") else (limit_price or 0.0)
                
                UpstoxService.log_audit(
                    f"[PAPER ORDER EXECUTED] ID={order_id} Symbol={symbol} Side={side} Status={status} FillPrice={price_filled}"
                )
                
                return {
                    "order_id": order_id,
                    "status": status,
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "order_type": order_type,
                    "price": price_filled,
                    "trading_mode": "PAPER",
                    "message": "Paper order processed successfully."
                }
            except Exception as e:
                UpstoxService.log_audit(
                    f"[PAPER ORDER REJECTED] Symbol={symbol} Side={side} Qty={quantity} Error={str(e)}"
                )
                raise
                
        elif mode == "LIVE":
            # STRICT SAFETY GATES (Section 6)
            
            # 1. Access Token Authentication Gate
            if not UpstoxService.ACCESS_TOKEN:
                msg = "LIVE trading mode error: Upstox access token is missing or expired. Re-authenticate first."
                UpstoxService.log_audit(f"[LIVE ORDER REJECTED] Symbol={symbol} Error={msg}")
                raise ValueError(msg)
                
            # 2. Risk Cap Gate (Server-side Enforcement)
            settings = get_settings()
            max_limit = settings.UPSTOX_MAX_ORDER_VALUE  # default ₹10,000
            
            # Get latest price to calculate total value
            try:
                quote = await MarketDataService.get_quote(symbol)
                current_price = float(quote["price"])
            except Exception as pe:
                logger.warning(f"Unable to fetch quote for risk cap verification: {pe}")
                # Fallback to limit price if quote fetch fails
                if order_type == "LIMIT" and limit_price:
                    current_price = limit_price
                else:
                    msg = f"LIVE trading mode error: Unable to verify current price for {symbol}."
                    UpstoxService.log_audit(f"[LIVE ORDER REJECTED] Symbol={symbol} Error={msg}")
                    raise ValueError(msg)
                    
            order_value = float(quantity) * (limit_price if order_type == "LIMIT" and limit_price else current_price)
            if order_value > max_limit:
                msg = f"LIVE order rejected: Value ₹{order_value:,.2f} exceeds per-order risk cap limit of ₹{max_limit:,.2f}."
                UpstoxService.log_audit(f"[LIVE ORDER REJECTED] User={user_id} Symbol={symbol} Side={side} Qty={quantity} Value=₹{order_value:,.2f} Error={msg}")
                raise ValueError(msg)
                
            # 3. Resolve symbol to Upstox key
            instrument_key = await UpstoxService.resolve_symbol(symbol)
            if not instrument_key:
                msg = f"LIVE order error: Could not map symbol {symbol} to a valid Upstox instrument."
                UpstoxService.log_audit(f"[LIVE ORDER REJECTED] Symbol={symbol} Error={msg}")
                raise ValueError(msg)
                
            # Log live order submission
            UpstoxService.log_audit(
                f"[LIVE ORDER SUBMITTING] User={user_id} Symbol={symbol} ({instrument_key}) Side={side} Qty={quantity} Type={order_type} Limit={limit_price} Value=₹{order_value:,.2f}"
            )
            
            # Send order to Upstox placement endpoint
            url = "https://api.upstox.com/v2/order/place"
            headers = {
                "Authorization": f"Bearer {UpstoxService.ACCESS_TOKEN}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            body = {
                "quantity": int(quantity),
                "product": product,  # "I" for Intraday, "D" for Delivery
                "validity": "DAY",
                "price": float(limit_price) if order_type == "LIMIT" and limit_price else 0.0,
                "tag": "NeuroQuant",
                "instrument_token": instrument_key,
                "order_type": "LIMIT" if order_type == "LIMIT" else "MARKET",
                "transaction_type": "BUY" if side == "BUY" else "SELL",
                "disclosed_quantity": 0,
                "trigger_price": 0.0,
                "is_amo": False
            }
            
            try:
                async with httpx.AsyncClient() as client:
                    r = await client.post(url, headers=headers, json=body, timeout=15.0)
                    
                    if r.status_code not in (200, 201):
                        err_msg = f"Upstox place order API returned error: status={r.status_code} body={r.text}"
                        UpstoxService.log_audit(f"[LIVE ORDER API ERROR] Symbol={symbol} Error={err_msg}")
                        raise ValueError(err_msg)
                        
                    res = r.json()
                    if res.get("status") != "success":
                        errors = res.get("errors", [])
                        err_str = ", ".join([e.get("message", "") for e in errors]) or "Unknown Upstox API error."
                        UpstoxService.log_audit(f"[LIVE ORDER REJECTED BY UPSTOX] Symbol={symbol} Error={err_str}")
                        raise ValueError(err_str)
                        
                    order_data = res.get("data", {})
                    order_id = order_data.get("order_id", "LIVE_API_ID")
                    
                    UpstoxService.log_audit(
                        f"[LIVE ORDER PLACED SUCCESS] ID={order_id} Symbol={symbol} Side={side} Qty={quantity} Type={order_type}"
                    )
                    
                    return {
                        "order_id": order_id,
                        "status": "ACCEPTED",
                        "symbol": symbol,
                        "side": side,
                        "quantity": quantity,
                        "order_type": order_type,
                        "price": limit_price or current_price,
                        "trading_mode": "LIVE",
                        "message": "Live order successfully accepted by Upstox."
                    }
            except Exception as e:
                UpstoxService.log_audit(
                    f"[LIVE ORDER EXCEPTION] Symbol={symbol} Side={side} Qty={quantity} Exception={str(e)}"
                )
                raise
                
        else:
            raise ValueError(f"Invalid trading mode: {mode}")

    @staticmethod
    async def cancel_order(
        order_id: str,
        symbol: str
    ) -> Dict[str, Any]:
        """Cancels an order."""
        mode = UpstoxService.TRADING_MODE
        symbol = symbol.upper().strip()
        
        if mode == "PAPER":
            UpstoxService.log_audit(f"[PAPER ORDER CANCEL REQUEST] ID={order_id}")
            # In paper trading, canceling is handled by deleting/updating the order state
            try:
                from app.database.connection import async_session_factory
                from app.models.paper_trading import PaperOrder
                from sqlalchemy import update
                async with async_session_factory() as session:
                    stmt = update(PaperOrder).where(PaperOrder.id == order_id).values(status="CANCELLED")
                    await session.execute(stmt)
                    await session.commit()
                UpstoxService.log_audit(f"[PAPER ORDER CANCELLED] ID={order_id}")
                return {"order_id": order_id, "status": "CANCELLED", "trading_mode": "PAPER"}
            except Exception as e:
                logger.error(f"Paper order cancellation failed: {e}")
                raise
                
        elif mode == "LIVE":
            if not UpstoxService.ACCESS_TOKEN:
                raise ValueError("Missing Upstox access token.")
                
            UpstoxService.log_audit(f"[LIVE ORDER CANCEL REQUEST] ID={order_id} Symbol={symbol}")
            
            # Send cancel order request to Upstox
            url = f"https://api.upstox.com/v2/order/cancel?order_id={order_id}"
            headers = {
                "Authorization": f"Bearer {UpstoxService.ACCESS_TOKEN}",
                "Accept": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                r = await client.delete(url, headers=headers, timeout=10.0)
                if r.status_code != 200:
                    err_msg = f"Upstox cancel order API error: {r.text}"
                    UpstoxService.log_audit(f"[LIVE ORDER CANCEL FAILED] ID={order_id} Error={err_msg}")
                    raise ValueError(err_msg)
                    
                res = r.json()
                if res.get("status") != "success":
                    errors = res.get("errors", [])
                    err_str = ", ".join([e.get("message", "") for e in errors]) or "Unknown Upstox API error."
                    UpstoxService.log_audit(f"[LIVE ORDER CANCEL FAILED] ID={order_id} Error={err_str}")
                    raise ValueError(err_str)
                    
                UpstoxService.log_audit(f"[LIVE ORDER CANCELLED SUCCESS] ID={order_id} Symbol={symbol}")
                return {"order_id": order_id, "status": "CANCELLED", "trading_mode": "LIVE"}
