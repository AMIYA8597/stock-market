# backend/app/services/alert_engine.py
"""Alert Engine – evaluates stock predictions and broadcasts buy/sell alerts."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import logging
from typing import List, Dict, Any

from app.services.prediction_engine import get_full_prediction

logger = logging.getLogger(__name__)

ALERT_THRESHOLDS = {
    "STRONG_BUY":   {"min_score": 0.40, "min_confidence": 0.70},
    "BUY":          {"min_score": 0.18, "min_confidence": 0.60},
    "STRONG_SELL":  {"min_score": -0.40, "min_confidence": 0.70},
    "SELL":         {"min_score": -0.18, "min_confidence": 0.60},
}

async def check_and_fire_alerts(symbols: list[str], websocket_manager) -> list[dict]:
    fired = []
    results = await asyncio.gather(*[get_full_prediction(s) for s in symbols], return_exceptions=True)
    
    for symbol, result in zip(symbols, results):
        if isinstance(result, Exception):
            logger.warning(f"Failed to get prediction for symbol={symbol} in alert check: {result}")
            continue
        if not result or not result.get("is_computed", False):
            continue
        
        ens = result["ensemble"]
        direction = ens["direction"]
        score = ens["raw_ensemble"]
        confidence = ens["confidence"]
        price = result["current_price"]
        
        threshold = ALERT_THRESHOLDS.get(direction)
        if not threshold:
            continue
        
        if abs(score) >= abs(threshold["min_score"]) and confidence >= threshold["min_confidence"]:
            forecast_5d = next((f["predicted_price"] for f in result["forecast"] if f["horizon_days"] == 5), None)
            
            alert = {
                "type": "signal_alert",
                "symbol": symbol.upper(),
                "direction": direction,
                "signal_score": round(score, 4),
                "confidence": round(confidence, 4),
                "current_price": price,
                "kelly_fraction": round(ens["kelly"], 4),
                "regime": ens["regime"]["regime"],
                "patterns": ens["pattern"]["patterns_detected"],
                "forecast_5d": forecast_5d,
                "timestamp": datetime.now(UTC).isoformat(),
                "message": f"{direction} signal for {symbol.upper()} at ₹{price:.2f} (confidence: {confidence:.0%})"
            }
            fired.append(alert)
            # Broadcast to WebSocket
            try:
                await websocket_manager.broadcast("signals:alerts", alert)
                logger.info(f"Broadcasted alert: {alert['message']}")
            except Exception as e:
                logger.warning(f"Failed to broadcast alert for {symbol}: {e}")
                
    return fired
