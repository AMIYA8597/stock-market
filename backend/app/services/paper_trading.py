"""Paper Trading Engine Service.

Handles wallet management, MARKET order fills, friction calculations,
position tracking, risk limits, daily loss circuit breakers, and LIMIT orders.
"""

from __future__ import annotations

from datetime import date, datetime, UTC
from decimal import Decimal
import logging
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper_trading import PaperWallet, PaperPosition, PaperOrder
from app.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class PaperTradingService:
    @staticmethod
    async def get_or_create_wallet(db: AsyncSession, user_id: str) -> PaperWallet:
        """Fetch the paper trading wallet for the user, or create one if missing."""
        stmt = select(PaperWallet).where(PaperWallet.user_id == user_id)
        res = await db.execute(stmt)
        wallet = res.scalar_one_or_none()

        if not wallet:
            wallet = PaperWallet(
                user_id=user_id,
                balance=Decimal("100000.00"),
                realized_pnl=Decimal("0.00"),
                daily_loss_limit=Decimal("5000.00"),
                last_reset_date=date.today(),
                daily_realized_loss=Decimal("0.00"),
            )
            db.add(wallet)
            await db.commit()
            await db.refresh(wallet)
            logger.info(f"Created new paper trading wallet for user_id={user_id}")

        return wallet

    @staticmethod
    async def get_positions(db: AsyncSession, user_id: str) -> list[dict]:
        """Fetch open positions with real-time mark-to-market unrealized P&L."""
        stmt = select(PaperPosition).where(PaperPosition.user_id == user_id)
        res = await db.execute(stmt)
        positions = res.scalars().all()

        results = []
        for pos in positions:
            symbol = pos.symbol
            qty = pos.quantity
            avg_price = pos.avg_buy_price

            # Fetch live price
            try:
                q = await MarketDataService.get_quote(symbol)
                curr_price = Decimal(str(q["price"]))
            except Exception:
                curr_price = avg_price

            unrealized_pnl = (curr_price - avg_price) * qty
            unrealized_pnl_pct = ((curr_price - avg_price) / avg_price * 100) if avg_price > 0 else Decimal("0.0")

            results.append({
                "id": str(pos.id),
                "symbol": symbol,
                "quantity": float(qty),
                "avg_buy_price": float(avg_price),
                "current_price": float(curr_price),
                "unrealized_pnl": float(round(unrealized_pnl, 2)),
                "unrealized_pnl_pct": float(round(unrealized_pnl_pct, 4)),
                "realized_pnl": float(round(pos.realized_pnl, 2)),
            })
        return results

    @staticmethod
    async def get_pnl(db: AsyncSession, user_id: str) -> dict:
        """Compute summary of paper trading wallet, holdings, equity, and P&L."""
        wallet = await PaperTradingService.get_or_create_wallet(db, user_id)
        
        # Reset daily realized loss if date has changed
        if wallet.last_reset_date != date.today():
            wallet.daily_realized_loss = Decimal("0.00")
            wallet.last_reset_date = date.today()
            await db.commit()

        positions = await PaperTradingService.get_positions(db, user_id)

        total_holdings_value = Decimal("0.0")
        total_unrealized_pnl = Decimal("0.0")

        for pos in positions:
            total_holdings_value += Decimal(str(pos["current_price"])) * Decimal(str(pos["quantity"]))
            total_unrealized_pnl += Decimal(str(pos["unrealized_pnl"]))

        total_equity = wallet.balance + total_holdings_value
        circuit_breaker_triggered = wallet.daily_realized_loss >= wallet.daily_loss_limit

        return {
            "cash_balance": float(round(wallet.balance, 2)),
            "total_holdings_value": float(round(total_holdings_value, 2)),
            "total_equity": float(round(total_equity, 2)),
            "realized_pnl": float(round(wallet.realized_pnl, 2)),
            "unrealized_pnl": float(round(total_unrealized_pnl, 2)),
            "daily_realized_loss": float(round(wallet.daily_realized_loss, 2)),
            "daily_loss_limit": float(round(wallet.daily_loss_limit, 2)),
            "circuit_breaker_triggered": circuit_breaker_triggered,
        }

    @staticmethod
    async def place_order(
        db: AsyncSession,
        user_id: str,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str,
        limit_price: float | None = None,
        signal_relation: str | None = None
    ) -> PaperOrder:
        """Place and execute a paper trading order."""
        sym = MarketDataService._normalize_symbol(symbol).upper().strip()
        side = side.upper().strip()
        order_type = order_type.upper().strip()

        if side not in ("BUY", "SELL"):
            raise ValueError("Side must be BUY or SELL")
        if order_type not in ("MARKET", "LIMIT"):
            raise ValueError("Order type must be MARKET or LIMIT")
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero")

        wallet = await PaperTradingService.get_or_create_wallet(db, user_id)
        
        # Reset daily realized loss if date has changed
        if wallet.last_reset_date != date.today():
            wallet.daily_realized_loss = Decimal("0.00")
            wallet.last_reset_date = date.today()

        # Check daily loss limit circuit breaker
        if side == "BUY" and wallet.daily_realized_loss >= wallet.daily_loss_limit:
            raise ValueError("Daily loss limit circuit breaker triggered. Buy orders are blocked.")

        # Get latest quote
        try:
            q = await MarketDataService.get_quote(sym)
            quote_price = Decimal(str(q["price"]))
        except Exception as e:
            logger.error(f"Failed to fetch quote for paper trade {sym}: {e}")
            raise ValueError(f"Could not retrieve live price for {sym}")

        # Check risk guardrail: order size limit (max 50% of total portfolio equity)
        pnl_summary = await PaperTradingService.get_pnl(db, user_id)
        total_equity = Decimal(str(pnl_summary["total_equity"]))
        order_price = Decimal(str(limit_price)) if order_type == "LIMIT" and limit_price is not None else quote_price
        order_value = Decimal(str(quantity)) * order_price
        
        if side == "BUY" and order_value > Decimal("0.5") * total_equity:
            raise ValueError(f"Order size ₹{order_value:,.2f} exceeds risk limit of 50% of portfolio equity (₹{Decimal('0.5') * total_equity:,.2f})")

        qty_dec = Decimal(str(quantity))

        # Determine signal relation (AGREEMENT, AGAINST, INDEPENDENT)
        if not signal_relation or signal_relation == "AUTO":
            signal_relation = "INDEPENDENT"
            try:
                from app.services.prediction_engine import get_full_prediction
                pred = await get_full_prediction(sym, bypass_cache=False)
                if pred and pred.get("is_computed", False):
                    ens = pred.get("ensemble", {})
                    direction = ens.get("direction", "NEUTRAL")
                    if direction in ("BUY", "STRONG_BUY", "BULLISH"):
                        signal_relation = "AGREEMENT" if side == "BUY" else "AGAINST"
                    elif direction in ("SELL", "STRONG_SELL", "BEARISH"):
                        signal_relation = "AGREEMENT" if side == "SELL" else "AGAINST"
                    else:
                        signal_relation = "INDEPENDENT"
            except Exception as e:
                logger.warning(f"Could not compute signal relation for order symbol={sym}: {e}")

        if order_type == "LIMIT":
            if limit_price is None or limit_price <= 0:
                raise ValueError("Limit price must be specified and greater than zero for LIMIT orders")
            
            lim_price_dec = Decimal(str(limit_price))
            gross_amount = qty_dec * lim_price_dec
            
            # Simple pre-flight checks for LIMIT orders
            if side == "BUY" and wallet.balance < gross_amount:
                raise ValueError(f"Insufficient cash balance for limit order. Required: ₹{gross_amount:,.2f}, Available: ₹{wallet.balance:,.2f}")
            elif side == "SELL":
                pos_stmt = select(PaperPosition).where(PaperPosition.user_id == user_id, PaperPosition.symbol == sym)
                pos_res = await db.execute(pos_stmt)
                pos = pos_res.scalar_one_or_none()
                if not pos or pos.quantity < qty_dec:
                    raise ValueError(f"Insufficient holdings of {sym} for limit order.")

            new_order = PaperOrder(
                user_id=user_id,
                symbol=sym,
                side=side,
                quantity=qty_dec,
                price=lim_price_dec,
                order_type="LIMIT",
                limit_price=lim_price_dec,
                status="PENDING",
                net_amount=gross_amount if side == "BUY" else -gross_amount,
                signal_relation=signal_relation,
            )
            db.add(new_order)
            await db.commit()
            await db.refresh(new_order)
            logger.info(f"Created PENDING limit order for user_id={user_id}, symbol={sym}")
            return new_order

        # MARKET order execution
        slippage_pct = Decimal("0.0005") # 0.05% slippage
        stt_pct = Decimal("0.001") # 0.1% STT

        gross_amount = qty_dec * quote_price
        brokerage = min(Decimal("20.00"), Decimal("0.0005") * gross_amount)
        stt = stt_pct * gross_amount
        slippage = slippage_pct * gross_amount

        if side == "BUY":
            execute_price = quote_price + (slippage / qty_dec)
            net_amount = gross_amount + brokerage + stt + slippage
            
            if wallet.balance < net_amount:
                raise ValueError(f"Insufficient cash balance. Required: ₹{net_amount:,.2f}, Available: ₹{wallet.balance:,.2f}")
            
            wallet.balance -= net_amount

            # Update position
            pos_stmt = select(PaperPosition).where(PaperPosition.user_id == user_id, PaperPosition.symbol == sym)
            pos_res = await db.execute(pos_stmt)
            pos = pos_res.scalar_one_or_none()

            if pos:
                new_qty = pos.quantity + qty_dec
                new_avg = (pos.quantity * pos.avg_buy_price + qty_dec * execute_price) / new_qty
                pos.quantity = new_qty
                pos.avg_buy_price = new_avg
            else:
                pos = PaperPosition(
                    user_id=user_id,
                    symbol=sym,
                    quantity=qty_dec,
                    avg_buy_price=execute_price,
                    realized_pnl=Decimal("0.00"),
                )
                db.add(pos)

        else: # SELL
            execute_price = quote_price - (slippage / qty_dec)
            net_amount = gross_amount - brokerage - stt - slippage

            pos_stmt = select(PaperPosition).where(PaperPosition.user_id == user_id, PaperPosition.symbol == sym)
            pos_res = await db.execute(pos_stmt)
            pos = pos_res.scalar_one_or_none()

            if not pos or pos.quantity < qty_dec:
                raise ValueError(f"Insufficient holdings of {sym} to sell. Owned: {pos.quantity if pos else 0}")

            wallet.balance += net_amount

            # Calculate realized P&L
            realized = qty_dec * (execute_price - pos.avg_buy_price) - (brokerage + stt + slippage)
            wallet.realized_pnl += realized
            pos.realized_pnl += realized

            if realized < 0:
                wallet.daily_realized_loss += abs(realized)

            pos.quantity -= qty_dec
            if pos.quantity <= 0:
                await db.delete(pos)

        new_order = PaperOrder(
            user_id=user_id,
            symbol=sym,
            side=side,
            quantity=qty_dec,
            price=execute_price,
            order_type="MARKET",
            status="FILLED",
            brokerage=brokerage,
            stt=stt,
            slippage=slippage,
            net_amount=net_amount,
            signal_relation=signal_relation,
        )
        db.add(new_order)
        await db.commit()
        await db.refresh(new_order)
        logger.info(f"Executed MARKET order for user_id={user_id}, symbol={sym}, side={side}, net_amount={net_amount}")
        return new_order

    @staticmethod
    async def check_and_execute_limit_orders(db: AsyncSession, symbol: str, current_price: Decimal) -> int:
        """Scan PENDING limit orders for symbol and fill them if price triggers are met."""
        sym = MarketDataService._normalize_symbol(symbol).upper().strip()
        
        # Query pending orders
        stmt = select(PaperOrder).where(
            PaperOrder.symbol == sym,
            PaperOrder.status == "PENDING"
        )
        res = await db.execute(stmt)
        pending_orders = res.scalars().all()

        filled_count = 0
        for order in pending_orders:
            trigger = False
            if order.side == "BUY" and current_price <= order.limit_price:
                trigger = True
            elif order.side == "SELL" and current_price >= order.limit_price:
                trigger = True

            if not trigger:
                continue

            # Execute the order
            wallet = await PaperTradingService.get_or_create_wallet(db, order.user_id)
            qty_dec = order.quantity
            limit_price_dec = order.limit_price

            slippage_pct = Decimal("0.0005") # 0.05% slippage
            stt_pct = Decimal("0.001") # 0.1% STT

            gross_amount = qty_dec * limit_price_dec
            brokerage = min(Decimal("20.00"), Decimal("0.0005") * gross_amount)
            stt = stt_pct * gross_amount
            slippage = slippage_pct * gross_amount

            if order.side == "BUY":
                execute_price = limit_price_dec + (slippage / qty_dec)
                net_amount = gross_amount + brokerage + stt + slippage

                if wallet.balance < net_amount:
                    order.status = "CANCELLED"
                    logger.warning(f"Cancelled limit BUY order {order.id} due to insufficient funds.")
                    continue

                wallet.balance -= net_amount

                # Update position
                pos_stmt = select(PaperPosition).where(PaperPosition.user_id == order.user_id, PaperPosition.symbol == sym)
                pos_res = await db.execute(pos_stmt)
                pos = pos_res.scalar_one_or_none()

                if pos:
                    new_qty = pos.quantity + qty_dec
                    new_avg = (pos.quantity * pos.avg_buy_price + qty_dec * execute_price) / new_qty
                    pos.quantity = new_qty
                    pos.avg_buy_price = new_avg
                else:
                    pos = PaperPosition(
                        user_id=order.user_id,
                        symbol=sym,
                        quantity=qty_dec,
                        avg_buy_price=execute_price,
                        realized_pnl=Decimal("0.00"),
                    )
                    db.add(pos)
            else: # SELL
                execute_price = limit_price_dec - (slippage / qty_dec)
                net_amount = gross_amount - brokerage - stt - slippage

                pos_stmt = select(PaperPosition).where(PaperPosition.user_id == order.user_id, PaperPosition.symbol == sym)
                pos_res = await db.execute(pos_stmt)
                pos = pos_res.scalar_one_or_none()

                if not pos or pos.quantity < qty_dec:
                    order.status = "CANCELLED"
                    logger.warning(f"Cancelled limit SELL order {order.id} due to insufficient holdings.")
                    continue

                wallet.balance += net_amount

                # Calculate realized P&L
                realized = qty_dec * (execute_price - pos.avg_buy_price) - (brokerage + stt + slippage)
                wallet.realized_pnl += realized
                pos.realized_pnl += realized

                if realized < 0:
                    wallet.daily_realized_loss += abs(realized)

                pos.quantity -= qty_dec
                if pos.quantity <= 0:
                    await db.delete(pos)

            # Update order details
            order.status = "FILLED"
            order.price = execute_price
            order.brokerage = brokerage
            order.stt = stt
            order.slippage = slippage
            order.net_amount = net_amount
            order.timestamp = datetime.now(UTC)
            filled_count += 1
            logger.info(f"FILLED pending limit order {order.id} for user {order.user_id} at {execute_price}")

        if filled_count > 0:
            await db.commit()

        return filled_count

    @staticmethod
    async def get_history(db: AsyncSession, user_id: str) -> list[dict]:
        """Fetch executed and pending orders log for the user."""
        stmt = select(PaperOrder).where(PaperOrder.user_id == user_id).order_by(PaperOrder.timestamp.desc())
        res = await db.execute(stmt)
        orders = res.scalars().all()

        return [
            {
                "id": str(o.id),
                "symbol": o.symbol,
                "side": o.side,
                "quantity": float(o.quantity),
                "price": float(o.price),
                "order_type": o.order_type,
                "limit_price": float(o.limit_price) if o.limit_price is not None else None,
                "status": o.status,
                "brokerage": float(o.brokerage),
                "stt": float(o.stt),
                "slippage": float(o.slippage),
                "net_amount": float(o.net_amount),
                "signal_relation": o.signal_relation,
                "timestamp": o.timestamp.isoformat(),
            }
            for o in orders
        ]

    @staticmethod
    async def reset_wallet(db: AsyncSession, user_id: str) -> dict:
        """Reset the virtual paper wallet back to starting balance of ₹1,00,000 and close positions."""
        # Delete positions
        del_pos_stmt = delete(PaperPosition).where(PaperPosition.user_id == user_id)
        await db.execute(del_pos_stmt)

        # Delete orders
        del_ord_stmt = delete(PaperOrder).where(PaperOrder.user_id == user_id)
        await db.execute(del_ord_stmt)

        # Update wallet
        stmt = select(PaperWallet).where(PaperWallet.user_id == user_id)
        res = await db.execute(stmt)
        wallet = res.scalar_one_or_none()

        if wallet:
            wallet.balance = Decimal("100000.00")
            wallet.realized_pnl = Decimal("0.00")
            wallet.daily_realized_loss = Decimal("0.00")
            wallet.last_reset_date = date.today()
        else:
            wallet = PaperWallet(
                user_id=user_id,
                balance=Decimal("100000.00"),
                realized_pnl=Decimal("0.00"),
                daily_loss_limit=Decimal("5000.00"),
                last_reset_date=date.today(),
                daily_realized_loss=Decimal("0.00"),
            )
            db.add(wallet)

        await db.commit()
        await db.refresh(wallet)
        logger.info(f"Reset paper trading wallet for user_id={user_id}")
        return await PaperTradingService.get_pnl(db, user_id)
