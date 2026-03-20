"""Alerts API endpoints with CRUD response contracts."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class AlertCreateRequest(BaseModel):
    symbol: str
    alert_type: str
    threshold: float | None = None
    conditions: Dict[str, Any] = Field(default_factory=dict)


class AlertUpdateRequest(BaseModel):
    threshold: float | None = None
    is_active: bool | None = None
    conditions: Dict[str, Any] | None = None


def _sample_alerts() -> List[Dict[str, Any]]:
    return [
        {
            "id": "alt-001",
            "name": "Reliance Breakout",
            "symbol": "RELIANCE.NS",
            "alert_type": "price",
            "threshold": 2500,
            "conditions": {"operator": "gt", "value": 2500},
            "channels": ["in_app"],
            "cooldown_minutes": 15,
            "is_active": True,
            "times_triggered": 3,
            "last_triggered_at": "2026-01-12T10:15:00Z",
            "created_at": "2026-01-01T09:00:00Z",
        },
        {
            "id": "alt-002",
            "name": "TCS Signal Change",
            "symbol": "TCS.NS",
            "alert_type": "ml_signal",
            "threshold": None,
            "conditions": {"signal": "BUY", "confidence_min": 0.75},
            "channels": ["in_app", "email"],
            "cooldown_minutes": 30,
            "is_active": True,
            "times_triggered": 1,
            "last_triggered_at": "2026-01-12T09:32:00Z",
            "created_at": "2026-01-02T08:15:00Z",
        },
    ]


def _sample_history(limit: int) -> List[Dict[str, Any]]:
    events = [
        {
            "id": "evt-001",
            "alert_id": "alt-001",
            "alert_name": "Reliance Breakout",
            "symbol": "RELIANCE.NS",
            "alert_type": "price",
            "severity": 3,
            "message": "Price crossed 2,500 resistance with above-average volume.",
            "payload": {"price": 2508.2, "volume_ratio": 1.9},
            "triggered_at": "2026-01-12T10:15:00Z",
        },
        {
            "id": "evt-002",
            "alert_id": "alt-002",
            "alert_name": "TCS Signal Change",
            "symbol": "TCS.NS",
            "alert_type": "ml_signal",
            "severity": 4,
            "message": "Model ensemble flipped to BUY with 79% confidence.",
            "payload": {"signal": "BUY", "confidence": 0.79},
            "triggered_at": "2026-01-12T09:32:00Z",
        },
        {
            "id": "evt-003",
            "alert_id": "alt-003",
            "alert_name": "NIFTY Volatility Spike",
            "symbol": "NIFTY50",
            "alert_type": "anomaly",
            "severity": 2,
            "message": "Intraday realized volatility moved above expected band.",
            "payload": {"rv": 0.023, "threshold": 0.018},
            "triggered_at": "2026-01-12T09:10:00Z",
        },
    ]
    return events[: max(limit, 0)]


ALERTS_DB: List[Dict[str, Any]] = _sample_alerts()
ALERT_EVENTS_DB: List[Dict[str, Any]] = _sample_history(50)


@router.post("/")
async def create_alert(payload: AlertCreateRequest):
    """Create a new user alert."""
    new_alert = {
        "id": f"alt-{len(ALERTS_DB) + 1:03d}",
        "name": f"{payload.symbol.upper()} {payload.alert_type.lower()} alert",
        "symbol": payload.symbol.upper(),
        "alert_type": payload.alert_type.lower(),
        "threshold": payload.threshold,
        "conditions": payload.conditions,
        "channels": ["in_app"],
        "cooldown_minutes": 15,
        "is_active": True,
        "times_triggered": 0,
        "last_triggered_at": None,
        "created_at": "2026-01-12T11:00:00Z",
    }
    ALERTS_DB.append(new_alert)
    return new_alert


@router.get("/")
async def list_alerts():
    """List active alerts for current user context."""
    return ALERTS_DB


@router.patch("/{alert_id}")
async def update_alert(alert_id: str, payload: AlertUpdateRequest):
    """Patch a previously created alert."""
    for item in ALERTS_DB:
        if item.get("id") == alert_id:
            if payload.threshold is not None:
                item["threshold"] = payload.threshold
            if payload.is_active is not None:
                item["is_active"] = payload.is_active
            if payload.conditions is not None:
                item["conditions"] = payload.conditions
            return item
    return {"id": alert_id, "status": "not_found"}


@router.delete("/{alert_id}")
async def delete_alert(alert_id: str):
    """Delete an alert by identifier."""
    for idx, item in enumerate(ALERTS_DB):
        if item.get("id") == alert_id:
            del ALERTS_DB[idx]
            return {"id": alert_id, "status": "deleted"}
    return {"id": alert_id, "status": "not_found"}


@router.get("/history")
async def alerts_history(limit: int = 50):
    """Return recent alert events in descending trigger time order."""
    return ALERT_EVENTS_DB[: max(limit, 0)]
