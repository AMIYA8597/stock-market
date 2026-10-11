"""Abstract base class for all deterministic and ML-driven trading strategies.

Every strategy must implement ``generate_signals`` which receives OHLCV data
(plus any auxiliary columns such as VWAP) and returns a list of ``StrategySignal``
objects.  The backtest engine feeds bars one at a time; strategies are free to
buffer history internally but **must not** look ahead: ``bar_index`` is the
current (closed) bar, and ``generate_signals`` is called **after** that bar's
close is final.
"""

from __future__ import annotations

import enum
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class TradeDirection(enum.StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(slots=True)
class StrategySignal:
    """A discrete entry signal emitted by a strategy."""

    bar_index: int
    direction: TradeDirection
    entry_price: float  # limit / stop-limit price for the order
    stop_loss: float
    take_profit: float
    risk_per_trade: float = 40.0  # account-currency risk
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def sl_distance(self) -> float:
        return abs(self.entry_price - self.stop_loss)

    @property
    def tp_distance(self) -> float:
        return abs(self.take_profit - self.entry_price)

    @property
    def reward_risk_ratio(self) -> float:
        if self.sl_distance == 0:
            return 0.0
        return self.tp_distance / self.sl_distance

    def lot_size(self, min_lots: float = 0.01, max_lots: float = 10.0,
                 point_value: float = 1.0) -> float:
        """Calculate position size from fixed-risk and SL distance.

        ``point_value`` converts price distance to account currency.
        For NSE equities it is 1 (₹ per share); for XAUUSD CFD it is
        100 (USD per oz per lot).
        """
        if self.sl_distance == 0:
            return min_lots
        raw = self.risk_per_trade / (self.sl_distance * point_value)
        return float(np.clip(raw, min_lots, max_lots))


@dataclass
class StrategyParams:
    """Container for strategy-specific parameters with validation."""

    _params: dict[str, Any] = field(default_factory=dict)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self._params[name]
        except KeyError:
            raise AttributeError(f"Parameter '{name}' not found") from None

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._params[name] = value

    def to_dict(self) -> dict[str, Any]:
        return dict(self._params)


class Strategy(ABC):
    """Base class every trading strategy must subclass.

    Subclasses implement:
    - ``name``: human-readable identifier
    - ``generate_signals(df, bar_index)``: return signals for the current bar
    - ``default_params()``: class method returning default parameters
    """

    name: str = "unnamed"
    description: str = ""
    version: str = "1.0.0"

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        defaults = self.default_params()
        if params:
            defaults.update(params)
        self.params = StrategyParams()
        for k, v in defaults.items():
            setattr(self.params, k, v)
        self._state: dict[str, Any] = {}  # mutable internal state

    @classmethod
    @abstractmethod
    def default_params(cls) -> dict[str, Any]:
        """Return a dict of parameter-name -> default-value."""
        ...

    @abstractmethod
    def generate_signals(
        self,
        df: pd.DataFrame,
        bar_index: int,
    ) -> list[StrategySignal]:
        """Inspect history up to (and including) ``bar_index`` and return signals.

        ``df`` has columns: open, high, low, close, volume, and optionally
        vwap, ema_9, ema_21, ema_50, ema_200, atr_14, adx_14, dmp_14, dmn_14, etc.

        Strategies MUST NOT read df.iloc[bar_index + 1:].
        """
        ...

    def reset(self) -> None:
        """Clear internal state between runs."""
        self._state.clear()

    def on_fill(self, bar_index: int, fill_price: float, direction: TradeDirection) -> None:  # noqa: B027
        """Called by the engine when an order is filled — update internal state."""

    def on_exit(self, bar_index: int, exit_price: float, result: str) -> None:  # noqa: B027
        """Called by the engine when a position is closed."""

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Pre-compute all indicators the strategy needs.

        Called once before the bar loop.  The returned DataFrame is passed
        to ``generate_signals`` on each bar.
        """
        return df

    def get_info(self) -> dict[str, Any]:
        """Return strategy metadata for the API."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "params": self.params.to_dict(),
        }
