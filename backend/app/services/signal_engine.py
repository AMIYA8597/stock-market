# backend/app/services/signal_engine.py
"""Signal Engine — Evaluates prediction output against strict trading rules and stores signals."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
import numpy as np

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Symbol
from app.models.signal import EnsembleSignal
from research.backtesting.cost_model import compute_costs

logger = logging.getLogger(__name__)


class SignalEngine:
    """Evaluates prediction data against risk thresholds, regimes, and cost models."""

    @staticmethod
    async def process_new_prediction(
        db: AsyncSession,
        symbol_ticker: str,
        prediction: dict,
    ) -> EnsembleSignal | None:
        """Process predictions and generate a trade signal if filters are passed."""
        # 1. Fetch Symbol ID from database
        stmt = select(Symbol).where(Symbol.ticker == symbol_ticker.upper())
        res = await db.execute(stmt)
        symbol = res.scalar_one_or_none()
        if not symbol:
            logger.warning(f"Symbol {symbol_ticker} not found in database, skipping signal generation.")
            return None

        # 2. Extract prediction metrics
        direction = prediction.get("direction", "NEUTRAL")
        confidence = float(prediction.get("confidence", 0.5))
        raw_ensemble = float(prediction.get("raw_ensemble", 0.0))
        regime = prediction.get("regime", {})
        regime_name = regime.get("regime", "SIDEWAYS")
        conditional_vol = regime.get("conditional_vol", 0.02)
        
        target_price_5d = float(prediction.get("target_price_5d", 0.0))
        stop_loss = float(prediction.get("stop_loss", 0.0))
        take_profit = float(prediction.get("take_profit", 0.0))
        kelly = float(prediction.get("kelly", 0.0))

        # Check latest closing price
        # (Default fallback values)
        technical = prediction.get("technical", {})
        current_price = float(technical.get("last_close") or prediction.get("current_price") or stop_loss)
        if current_price <= 0:
            current_price = stop_loss

        # 3. Rule 1: Confidence Threshold Check
        # Confidence must be > 65% for directional action
        if confidence < 0.65:
            logger.info(f"Signal rejected for {symbol_ticker}: Confidence {confidence:.2%} is below 65% threshold.")
            return None

        # 4. Rule 2: Regime Filter
        # BUY signals are blocked during BEAR or CRISIS HMM states
        if direction in ("BUY", "STRONG_BUY") and regime_name in ("BEAR", "CRISIS"):
            logger.info(f"Signal rejected for {symbol_ticker}: BUY direction is incompatible with HMM regime {regime_name}.")
            return None
        
        # SELL signals are blocked during BULL states
        if direction in ("SELL", "STRONG_SELL") and regime_name == "BULL":
            logger.info(f"Signal rejected for {symbol_ticker}: SELL direction is incompatible with HMM regime {regime_name}.")
            return None

        # 5. Rule 3: Risk/Reward Ratio Check (Cost Adjusted)
        # Expected Reward must exceed 3x estimated round-trip transaction costs
        # Cost parameters: Adv daily volume = 10,000,000 (standard large cap)
        trades_abs = np.array([[1.0]])
        prices = np.array([[current_price]])
        adv = np.array([[10000000.0]])
        realized_vol = np.array([[conditional_vol]])
        
        # Calculate single-trip cost
        cost_arr = compute_costs(trades_abs, prices, adv, realized_vol)
        single_trip_cost = float(cost_arr[0][0])
        round_trip_cost = single_trip_cost * 2.0
        
        expected_gain = abs(target_price_5d - current_price)
        if expected_gain < (3.0 * round_trip_cost):
            logger.info(
                f"Signal rejected for {symbol_ticker}: Expected gain (₹{expected_gain:.2f}) "
                f"does not exceed 3x round-trip cost (₹{3.0 * round_trip_cost:.2f})."
            )
            return None

        # 6. Build and store the approved EnsembleSignal
        regime_map = {"bull": 0, "bear": 1, "sideways": 2, "crisis": 3, "BULL": 0, "BEAR": 1, "SIDEWAYS": 2, "CRISIS": 3}
        regime_state = regime_map.get(regime_name, 2)

        inputs_dict = {
            "technical_score": float(technical.get("score", 0.0)),
            "pattern_score": float(prediction.get("pattern", {}).get("pattern_score", 0.0)),
            "momentum_score": float(prediction.get("momentum", {}).get("momentum_score", 0.0)),
            "xgboost_score": float(prediction.get("xgboost", {}).get("xgb_score", 0.0)),
            "sentiment_score": float(prediction.get("online_learner", {}).get("raw_signal", 0.0)),
        }

        # Check if a signal already exists for this exact timestamp and symbol
        signal_time = datetime.now(UTC)
        
        ensemble_signal = EnsembleSignal(
            time=signal_time,
            symbol_id=symbol.id,
            signal=Decimal(str(round(raw_ensemble, 4))),
            confidence=Decimal(str(round(confidence, 4))),
            direction=direction,
            model_weights=prediction.get("model_weights") or {},
            regime_state=regime_state,
            kelly_fraction=Decimal(str(round(kelly, 4))) if kelly > 0 else Decimal("0.0"),
            inputs_used=inputs_dict,
            outcome="PENDING",
        )

        db.add(ensemble_signal)
        await db.flush()
        logger.info(f"Generated new EnsembleSignal for {symbol_ticker}: {direction} @ {confidence:.2%} confidence.")
        return ensemble_signal
