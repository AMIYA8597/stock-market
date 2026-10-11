"""Strategy registry — discover, instantiate, and list available strategies.

Usage::

    from research.strategies.registry import get_strategy, list_strategies

    # List all registered strategy names
    names = list_strategies()

    # Instantiate a strategy by name with optional param overrides
    strat = get_strategy("ema_cross_vwap_adx", params={"adx_threshold": 25})
"""

from __future__ import annotations

import logging
from typing import Any

from research.strategies.base import Strategy

logger = logging.getLogger(__name__)

# ── Private registry ────────────────────────────────────────────────────

_REGISTRY: dict[str, type[Strategy]] = {}


def register_strategy(cls: type[Strategy]) -> type[Strategy]:
    """Register a Strategy subclass by its ``name`` attribute.

    Can be used as a decorator::

        @register_strategy
        class MyStrategy(Strategy):
            name = "my_strategy"
            ...

    Or called explicitly::

        register_strategy(MyStrategy)
    """
    if not issubclass(cls, Strategy):
        raise TypeError(f"{cls} is not a Strategy subclass")

    name = cls.name
    if name == "unnamed":
        raise ValueError(f"Strategy {cls.__name__} has no name set")

    if name in _REGISTRY and _REGISTRY[name] is not cls:
        logger.warning(
            "Strategy '%s' already registered (%s); overwriting with %s",
            name,
            _REGISTRY[name].__name__,
            cls.__name__,
        )

    _REGISTRY[name] = cls
    return cls


def get_strategy(name: str, params: dict[str, Any] | None = None) -> Strategy:
    """Instantiate a registered strategy by name.

    Raises ``KeyError`` if the strategy is not registered.
    """
    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY.keys()))
        raise KeyError(
            f"Strategy '{name}' not found. Available: {available}"
        )
    return _REGISTRY[name](params=params)


def list_strategies() -> list[dict[str, Any]]:
    """Return metadata for all registered strategies."""
    result = []
    for name in sorted(_REGISTRY.keys()):
        cls = _REGISTRY[name]
        result.append({
            "name": cls.name,
            "description": cls.description,
            "version": cls.version,
            "default_params": cls.default_params(),
        })
    return result


# ── Auto-register built-in strategies ───────────────────────────────────

def _auto_register() -> None:
    """Import and register all built-in strategies."""
    from research.strategies.ema_cross_vwap_adx import EMACrossVWAPADXStrategy
    from research.strategies.ema_retest import EMARetestStrategy

    register_strategy(EMACrossVWAPADXStrategy)
    register_strategy(EMARetestStrategy)


_auto_register()
