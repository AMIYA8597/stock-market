import asyncio
import logging
from datetime import UTC, datetime

from celery import shared_task
from sqlalchemy import desc, select

from app.core.websocket_manager import ws_manager
from app.database.connection import async_session_factory
from app.models.alerts import Alert
from app.models.instrument import Instrument
from app.models.market import QuoteSnapshot

logger = logging.getLogger(__name__)

async def _evaluate_alerts():
    async with async_session_factory() as session:
        stmt = (
            select(Alert, Instrument)
            .outerjoin(Instrument, Alert.instrument_id == Instrument.id)
            .where(Alert.enabled.is_(True), Alert.is_triggered.is_(False))
        )
        result = await session.execute(stmt)
        rows = result.all()

        for alert, instrument in rows:
            if not instrument:
                continue

            symbol = instrument.canonical_symbol

            try:
                # Fetch latest quote snapshot from DB
                quote_stmt = (
                    select(QuoteSnapshot)
                    .where(QuoteSnapshot.instrument_id == instrument.id)
                    .order_by(desc(QuoteSnapshot.observed_at))
                    .limit(1)
                )
                quote_result = await session.execute(quote_stmt)
                quote = quote_result.scalar_one_or_none()

                if not quote or quote.price is None:
                    continue

                price = float(quote.price)
                threshold = float(alert.threshold) if alert.threshold else None

                triggered = False
                if alert.alert_type == "PRICE_ABOVE" and threshold is not None:
                    if price >= threshold:
                        triggered = True
                elif alert.alert_type == "PRICE_BELOW" and threshold is not None:
                    if price <= threshold:
                        triggered = True
                elif alert.alert_type == "PERCENT_UP":
                    base_price = float(quote.previous_close or 0)
                    if base_price > 0 and ((price - base_price) / base_price * 100) >= threshold:
                        triggered = True
                elif alert.alert_type == "PERCENT_DOWN":
                    base_price = float(quote.previous_close or 0)
                    if base_price > 0 and ((base_price - price) / base_price * 100) >= threshold:
                        triggered = True

                if triggered:
                    alert.is_triggered = True
                    alert.triggered_at = datetime.now(UTC)
                    alert.enabled = False
                    await session.commit()

                    logger.info(f"Alert {alert.id} TRIGGERED for {symbol} at {price}")

                    # Deduplication / Notification state is saved as is_triggered=True
                    # Notification Delivery
                    user_id = str(alert.user_id)
                    event_payload = {
                        "type": "alert.triggered",
                        "channel": f"alerts:{user_id}",
                        "event_id": str(alert.id),
                        "symbol": symbol,
                        "payload": {
                            "alert_id": str(alert.id),
                            "alert_type": alert.alert_type,
                            "threshold": float(alert.threshold),
                            "trigger_price": price,
                            "triggered_at": alert.triggered_at.isoformat(),
                        },
                        "ts": datetime.now(UTC).isoformat(),
                        "source": "DATABASE"
                    }
                    try:
                        await ws_manager.broadcast(f"alerts:{user_id}", event_payload)
                    except Exception as we:
                        logger.warning(f"Failed to broadcast alert {alert.id}: {we}")

            except Exception as e:
                logger.warning(f"Failed to evaluate alert {alert.id} for {symbol}: {e}")

@shared_task(name="evaluate_market_alerts")
def evaluate_market_alerts():
    """Durable job to evaluate alerts against canonical DB state."""
    asyncio.run(_evaluate_alerts())
