"""Static ensemble weighting.

This file replaces the legacy rolling-Sharpe dynamic weighting system with the strictly bounded static rules defined in SIGNALS.md.
"""

from __future__ import annotations


def get_fixed_weights() -> dict[str, float]:
    return {"technical": 0.4, "ml": 0.6}
