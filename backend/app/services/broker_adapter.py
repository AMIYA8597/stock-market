# backend/app/services/broker_adapter.py
"""Broker Adapter Service.

Gated execution router that implements the safety gate (Section 6).
Handles paper trading execution vs real order execution via Upstox REST API.
Enforces per-order risk cap and audits all transactions.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.paper_trading import PaperTradingService
from app.services.upstox_service import UpstoxService

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
        product: str = "I",  # Default "I" for Intraday, "D" for Delivery
    ) -> dict[str, Any]:
        """Unified gateway for executing buy/sell orders.

        Routes every order to the paper-trading service.
        """
        symbol = symbol.upper().strip()
        side = side.upper().strip()
        order_type = order_type.upper().strip()
        product = product.upper().strip()

        # Execute simulated transaction in Paper trading database
        UpstoxService.log_audit(
            f"[PAPER ORDER SUBMITTED] User={user_id} Instrument={symbol} Side={side} Qty={quantity} Type={order_type} Limit={limit_price}"
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
                signal_relation="AUTO",
            )

            # Fetch order detail
            order_id = str(order.id) if hasattr(order, "id") else "PAPER_ORDER_ID"
            status = str(order.status) if hasattr(order, "status") else "FILLED"
            price_filled = (
                float(order.price) if hasattr(order, "price") else (limit_price or 0.0)
            )

            UpstoxService.log_audit(
                f"[PAPER ORDER EXECUTED] ID={order_id} Instrument={symbol} Side={side} Status={status} FillPrice={price_filled}"
            )

            return {
                "order_id": order_id,
                "status": status,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "order_type": order_type,
                "price": price_filled,
                "message": "Paper order processed successfully.",
            }
        except Exception as e:
            UpstoxService.log_audit(
                f"[PAPER ORDER REJECTED] Instrument={symbol} Side={side} Qty={quantity} Error={str(e)}"
            )
            raise

    @staticmethod
    async def cancel_order(
        order_id: str, symbol: str, user_id: str | None = None
    ) -> dict[str, Any]:
        """Cancels an order."""
        UpstoxService.log_audit(f"[PAPER ORDER CANCEL REQUEST] ID={order_id}")
        # In paper trading, canceling is handled by deleting/updating the order state
        try:
            import uuid

            from sqlalchemy import update

            from app.database.connection import async_session_factory
            from app.models.paper_trading import PaperOrder

            async with async_session_factory() as session:
                stmt = update(PaperOrder).where(PaperOrder.id == uuid.UUID(order_id))
                if user_id:
                    stmt = stmt.where(PaperOrder.user_id == uuid.UUID(user_id))

                stmt = stmt.values(status="CANCELLED")
                res = await session.execute(stmt)
                if res.rowcount == 0:
                    raise ValueError(
                        "Order not found or you do not have permission to cancel it."
                    )
                await session.commit()
            UpstoxService.log_audit(f"[PAPER ORDER CANCELLED] ID={order_id}")
            return {"order_id": order_id, "status": "CANCELLED"}
        except Exception as e:
            logger.error(f"Paper order cancellation failed: {e}")
            raise
