import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.database.connection import async_session_factory
from app.models.alert import Alert
from app.models.instrument import Instrument
from app.services.data_ingestion.provider_manager import provider_manager

logger = logging.getLogger(__name__)


class AlertEvaluator:
    def __init__(self, interval_seconds: int = 60):
        self.interval_seconds = interval_seconds
        self._running = False
        self._task = None

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("AlertEvaluator started.")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("AlertEvaluator stopped.")

    async def _run_loop(self):
        while self._running:
            try:
                await self.evaluate_alerts()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error evaluating alerts: {e}")
            await asyncio.sleep(self.interval_seconds)

    async def evaluate_alerts(self):
        async with async_session_factory() as session:
            stmt = (
                select(Alert, Instrument.symbol)
                .outerjoin(Instrument, Alert.instrument_id == Instrument.id)
                .where(Alert.enabled.is_(True), Alert.is_triggered.is_(False))
            )
            result = await session.execute(stmt)
            rows = result.all()

            for alert, symbol in rows:
                if not symbol:
                    continue  # Portfolio level alerts not supported here yet

                try:
                    quote = await provider_manager.get_quote(symbol)
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

                    if triggered:
                        alert.is_triggered = True
                        alert.triggered_at = datetime.now(UTC)
                        alert.enabled = False
                        await session.commit()
                        logger.info(f"Alert {alert.id} TRIGGERED for {symbol} at {price}")
                        # Next phase: send WebSocket/Push Notification here

                except Exception as e:
                    logger.warning(f"Failed to evaluate alert {alert.id} for {symbol}: {e}")


evaluator = AlertEvaluator()
