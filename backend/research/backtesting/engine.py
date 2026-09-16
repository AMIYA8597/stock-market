"""Event-driven backtest engine simulating next-bar execution without look-ahead bias."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

from research.backtesting.cost_model import compute_indian_costs

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BacktestResult:
    daily_returns: np.ndarray
    pnl: np.ndarray
    equity_curve: np.ndarray
    positions: np.ndarray
    costs: np.ndarray
    trades_log: list[dict[str, Any]]


class EventDrivenBacktester:
    """Iterates through historical bars to simulate real-time paper trading."""

    def __init__(
        self,
        prices: np.ndarray,
        signals: np.ndarray,
        dates: np.ndarray,
        initial_capital: float = 100000.0,
        kelly_fraction: np.ndarray | None = None,
        target_vol: float = 0.15,
    ):
        self.prices = np.asarray(prices, dtype=float)
        self.signals = np.asarray(signals, dtype=float)
        self.dates = np.asarray(dates)
        self.initial_capital = initial_capital

        if kelly_fraction is not None:
            self.kelly_fraction = np.asarray(kelly_fraction, dtype=float)
        else:
            self.kelly_fraction = np.ones_like(self.signals)

        self.target_vol = target_vol

        self.num_steps = len(self.prices)

        # State tracking
        self.cash = initial_capital
        self.position_qty = 0.0
        self.avg_price = 0.0

        # Metrics tracking arrays
        self.equity_curve = np.zeros(self.num_steps)
        self.pnl = np.zeros(self.num_steps)
        self.positions = np.zeros(self.num_steps)
        self.daily_returns = np.zeros(self.num_steps)
        self.costs_array = np.zeros(self.num_steps)
        self.trades_log = []

    def _apply_constraints(self, target_exposure: float) -> float:
        # Hard limits on max gross and net exposure
        max_gross = 2.0
        return np.clip(target_exposure, -max_gross, max_gross)

    def run(self, progress_callback=None) -> BacktestResult:
        """Run the event-driven simulation."""

        # First pass to compute realized volatility for sizing
        returns = np.zeros_like(self.prices)
        returns[1:] = (
            self.prices[1:] / np.where(self.prices[:-1] == 0, np.nan, self.prices[:-1]) - 1.0
        )
        returns = np.nan_to_num(returns, nan=0.0)

        realized_vol = np.full_like(self.prices, fill_value=np.nan)
        window = 21
        for t in range(window - 1, self.num_steps):
            realized_vol[t] = np.std(returns[t - window + 1 : t + 1], ddof=1) * np.sqrt(252.0)

        vol_scalars = self.target_vol / np.where(realized_vol <= 0.0, np.nan, realized_vol)
        vol_scalars = np.nan_to_num(vol_scalars, nan=1.0, posinf=1.0, neginf=1.0)

        # Step through time
        for t in range(self.num_steps):
            current_price = self.prices[t]
            self.dates[t]

            # 1. Update mark-to-market
            holdings_value = self.position_qty * current_price
            equity = self.cash + holdings_value

            # 2. Record daily metrics
            self.equity_curve[t] = equity
            self.positions[t] = self.position_qty

            if t > 0:
                self.pnl[t] = equity - self.equity_curve[t - 1]
                if self.equity_curve[t - 1] > 0:
                    self.daily_returns[t] = self.pnl[t] / self.equity_curve[t - 1]

            # 3. Determine target position size for TOMORROW'S OPEN based on TODAY'S close signal
            # This ensures no look-ahead bias
            if t < self.num_steps - 1:
                # Target exposure = Signal (-1 to 1) * Kelly * Volatility Scalar
                raw_target_exposure = self.signals[t] * self.kelly_fraction[t] * vol_scalars[t]
                target_exposure = self._apply_constraints(raw_target_exposure)

                # Desired Notional
                target_notional = target_exposure * equity

                # Desired quantity
                if current_price > 0:
                    target_qty = target_notional / current_price
                else:
                    target_qty = 0.0

                # 4. Calculate delta
                qty_delta = target_qty - self.position_qty

                if abs(qty_delta) > 1e-6:
                    # In a real system, trade executes next bar open.
                    # We will simulate execution at next bar's close price for simplicity (daily bars).
                    next_price = self.prices[t + 1]
                    gross_value = abs(qty_delta) * next_price
                    side = "BUY" if qty_delta > 0 else "SELL"

                    # Compute costs
                    cost_breakdown = compute_indian_costs(
                        gross_amount=gross_value, side=side, is_delivery=True, slippage_pct=0.0005
                    )
                    total_cost = cost_breakdown["total_cost"]

                    # Execute Trade
                    if side == "BUY":
                        self.cash -= gross_value + total_cost

                        # Update Avg Price
                        total_qty = self.position_qty + qty_delta
                        if total_qty != 0:
                            self.avg_price = (
                                self.position_qty * self.avg_price + qty_delta * next_price
                            ) / total_qty
                        self.position_qty += qty_delta
                    else:
                        self.cash += gross_value - total_cost
                        self.position_qty += qty_delta
                        if abs(self.position_qty) < 1e-6:
                            self.position_qty = 0.0
                            self.avg_price = 0.0

                    # Assign cost to TOMORROW since trade happens tomorrow
                    self.costs_array[t + 1] += total_cost

                    # Log trade
                    self.trades_log.append(
                        {
                            "date": str(self.dates[t + 1]),
                            "side": side,
                            "qty": qty_delta,
                            "price": next_price,
                            "cost": total_cost,
                            "equity_after": self.cash + (self.position_qty * next_price),
                        }
                    )

            if progress_callback and t % max(1, self.num_steps // 20) == 0:
                progress_callback(int((t / self.num_steps) * 100))

        return BacktestResult(
            daily_returns=self.daily_returns,
            pnl=self.pnl,
            equity_curve=self.equity_curve,
            positions=self.positions,
            costs=self.costs_array,
            trades_log=self.trades_log,
        )


def run_vectorized_backtest(
    signals: np.ndarray,
    prices: np.ndarray,
    kelly_fraction: np.ndarray,
    initial_capital: float = 100000.0,
) -> BacktestResult:
    n = prices.shape[0] if len(prices.shape) > 0 else 0
    returns = np.zeros(n)
    pnl = np.zeros(n)
    equity = np.ones(n) * initial_capital
    return BacktestResult(daily_returns=returns, pnl=pnl, equity_curve=equity)
