"""Shared numeric helpers for API response serialization."""

import logging
import math

logger = logging.getLogger(__name__)


def safe_round(val: float | None, places: int) -> float:
    """Round a float for wire serialization, guarding against NaN/Inf.

    A NaN/Inf value here means the underlying metric is genuinely undefined
    (e.g. Sharpe ratio with zero volatility), not that it equals zero. The
    response schemas this feeds are non-nullable Decimal fields, so the
    metric is coerced to 0.0 rather than failing the whole response — but
    that coercion is logged so it never passes as a silent, accidental fact.
    """
    if val is None or math.isnan(val) or math.isinf(val):
        logger.warning("safe_round: coercing undefined value (%r) to 0.0", val)
        return 0.0
    return round(float(val), places)
