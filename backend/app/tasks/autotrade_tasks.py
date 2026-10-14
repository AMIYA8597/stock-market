"""Scheduled scan: turns live AI signals into real paper trades for users
who have explicitly opted in (see app.models.autotrade.AutoTradeSetting).

This is the "AI decides and trades by itself" loop -- it calls the same
ensemble prediction engine the Signals page reads, and for each symbol in
the user's chosen watchlist that crosses their configured confidence
threshold, places an order through BrokerAdapter (which enforces the real
per-order 50%-of-equity cap, daily loss circuit breaker, and margin checks
already implemented in PaperTradingService.place_order).

BrokerAdapter.place_order is hardcoded to paper trading regardless of what
this task decides -- it never touches a real broker or a real bank
account. Wiring real-money execution is a separate, explicit step that
requires real Upstox API credentials and is not done here.
"""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import UTC, datetime

from celery import shared_task
from sqlalchemy import func, select

from app.core.config import get_settings
from app.database.connection import async_session_factory
from app.models.autotrade import AutoTradeSetting
from app.models.paper_trading import PaperPosition
from app.models.watchlist import UserWatchlist
from app.services.broker_adapter import BrokerAdapter
from app.services.market_data_service import MarketDataService
from app.services.paper_trading import PaperTradingService
from app.services.prediction_engine import get_full_prediction

logger = logging.getLogger(__name__)

_DIRECTION_TO_SIDE = {
    "BUY": "BUY",
    "STRONG_BUY": "BUY",
    "BULLISH": "BUY",
    "SELL": "SELL",
    "STRONG_SELL": "SELL",
    "BEARISH": "SELL",
}


async def _scan_one_user(setting: AutoTradeSetting) -> dict:
    """Evaluate one opted-in user's watchlist and place any qualifying orders."""
    user_id = str(setting.user_id)
    placed: list[dict] = []
    skipped: list[dict] = []

    async with async_session_factory() as db:
        wl_res = await db.execute(
            select(UserWatchlist.symbol).where(
                UserWatchlist.user_id == setting.user_id,
                UserWatchlist.list_id == setting.watchlist_id,
            )
        )
        symbols = wl_res.scalars().all()
        if not symbols:
            return {"user_id": user_id, "placed": [], "skipped": [], "note": "watchlist empty"}

        open_count_res = await db.execute(
            select(func.count())
            .select_from(PaperPosition)
            .where(PaperPosition.user_id == setting.user_id, PaperPosition.quantity > 0)
        )
        open_positions = open_count_res.scalar_one()

        for symbol in symbols:
            try:
                pred = await get_full_prediction(symbol, bypass_cache=True)
            except Exception as e:
                skipped.append({"symbol": symbol, "reason": f"prediction failed: {e}"})
                continue

            if not pred or not pred.get("is_computed"):
                skipped.append({"symbol": symbol, "reason": "prediction not computed"})
                continue

            ensemble = pred.get("ensemble", {}) or {}
            direction = ensemble.get("direction", "NEUTRAL")
            confidence_raw = float(ensemble.get("confidence", 0.0) or 0.0)
            confidence_pct = confidence_raw * 100.0 if confidence_raw <= 1.0 else confidence_raw
            side = _DIRECTION_TO_SIDE.get(direction)

            if not side or confidence_pct < float(setting.min_confidence):
                skipped.append(
                    {
                        "symbol": symbol,
                        "reason": f"direction={direction} confidence={confidence_pct:.1f}%",
                    }
                )
                continue

            pos_res = await db.execute(
                select(PaperPosition).where(
                    PaperPosition.user_id == setting.user_id, PaperPosition.symbol == symbol
                )
            )
            existing = pos_res.scalar_one_or_none()
            has_long = bool(existing and float(existing.quantity) > 0)

            if side == "BUY" and has_long:
                skipped.append({"symbol": symbol, "reason": "already holding a long position"})
                continue
            if side == "SELL" and not has_long:
                skipped.append({"symbol": symbol, "reason": "no long position to exit"})
                continue
            if side == "BUY" and open_positions >= setting.max_open_positions:
                skipped.append({"symbol": symbol, "reason": "max_open_positions reached"})
                continue

            try:
                if side == "SELL":
                    quantity = float(existing.quantity)
                else:
                    wallet = await PaperTradingService.get_or_create_wallet(db, user_id)
                    quote = await MarketDataService.get_quote(symbol)
                    raw_timestamp = quote.get("timestamp")
                    if not isinstance(raw_timestamp, str):
                        skipped.append({"symbol": symbol, "reason": "quote timestamp unavailable"})
                        continue
                    try:
                        quote_timestamp = datetime.fromisoformat(raw_timestamp)
                    except ValueError:
                        skipped.append({"symbol": symbol, "reason": "quote timestamp invalid"})
                        continue
                    if quote_timestamp.tzinfo is None:
                        quote_timestamp = quote_timestamp.replace(tzinfo=UTC)
                    quote_age = (datetime.now(UTC) - quote_timestamp).total_seconds()
                    if quote_age < 0 or quote_age > get_settings().AUTOTRADE_MAX_QUOTE_AGE_SECONDS:
                        skipped.append(
                            {
                                "symbol": symbol,
                                "reason": f"quote stale or out of order ({quote_age:.1f}s)",
                            }
                        )
                        continue
                    price = float(quote["price"])
                    if price <= 0:
                        skipped.append({"symbol": symbol, "reason": "invalid quote price"})
                        continue
                    risk_amount = float(wallet.balance) * float(setting.risk_per_trade_pct)
                    quantity = math.floor(risk_amount / price)
                    if quantity < 1:
                        skipped.append({"symbol": symbol, "reason": "sized quantity below 1 share"})
                        continue

                result = await BrokerAdapter.place_order(
                    db=db,
                    user_id=user_id,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    order_type="MARKET",
                )
                placed.append(
                    {"symbol": symbol, "side": side, "quantity": quantity, "result": result}
                )
                if side == "BUY":
                    open_positions += 1
                logger.info(f"[AUTOTRADE] user={user_id} {side} {quantity} {symbol}")
            except Exception as e:
                skipped.append({"symbol": symbol, "reason": f"order rejected: {e}"})
                logger.warning(f"[AUTOTRADE] user={user_id} order rejected for {symbol}: {e}")

        setting_res = await db.execute(
            select(AutoTradeSetting).where(AutoTradeSetting.id == setting.id)
        )
        live_setting = setting_res.scalar_one_or_none()
        if live_setting:
            live_setting.last_scan_at = datetime.now(UTC)
            live_setting.last_scan_result = {"placed": placed, "skipped": skipped}
            await db.commit()

    return {"user_id": user_id, "placed": placed, "skipped": skipped}


async def run_autotrade_scan_async() -> None:
    async with async_session_factory() as db:
        res = await db.execute(select(AutoTradeSetting).where(AutoTradeSetting.enabled.is_(True)))
        settings_rows = list(res.scalars().all())

    if not settings_rows:
        logger.info("[AUTOTRADE] No users have auto-trading enabled. Skipping scan.")
        return

    for setting in settings_rows:
        try:
            await _scan_one_user(setting)
        except Exception as e:
            logger.exception(f"[AUTOTRADE] Scan failed for user={setting.user_id}: {e}")


@shared_task(name="run_autotrade_scan")
def run_autotrade_scan() -> None:
    """Celery entry point -- see module docstring for what this does."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(run_autotrade_scan_async())
        return

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(asyncio.run, run_autotrade_scan_async()).result()
