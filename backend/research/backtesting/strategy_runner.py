"""Strategy-driven backtest runner.

Accepts a ``Strategy`` object and OHLCV DataFrame, iterates bar-by-bar,
manages pending orders (buy-stop / sell-stop), tracks open positions with
SL/TP exit logic, and produces a full ``StrategyBacktestResult``.

This complements the existing ``EventDrivenBacktester`` (signal-array based)
by working with the richer ``StrategySignal`` objects that carry entry, SL,
and TP levels.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from research.backtesting.cost_model import compute_indian_costs
from research.strategies.base import Strategy, StrategySignal, TradeDirection

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TradeRecord:
    """One completed round-trip trade."""

    entry_bar: int
    exit_bar: int
    direction: str
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit: float
    lots: float
    pnl_gross: float
    cost: float
    pnl_net: float
    result: str  # "TP", "SL", "CANCEL", "END"
    risk_per_trade: float
    r_multiple: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class StrategyBacktestResult:
    """Full results from a strategy-driven backtest."""

    strategy_name: str
    trades: list[TradeRecord]
    equity_curve: np.ndarray
    daily_returns: np.ndarray
    initial_capital: float
    final_equity: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    total_pnl_net: float
    total_cost: float
    max_drawdown: float
    max_drawdown_duration: int
    avg_r_multiple: float
    expectancy_r: float
    sharpe: float
    sortino: float

    def summary(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy_name,
            "total_trades": self.total_trades,
            "win_rate": round(self.win_rate, 4),
            "profit_factor": round(self.profit_factor, 4),
            "total_pnl_net": round(self.total_pnl_net, 2),
            "total_cost": round(self.total_cost, 2),
            "max_drawdown": round(self.max_drawdown, 4),
            "max_drawdown_duration": self.max_drawdown_duration,
            "avg_r_multiple": round(self.avg_r_multiple, 4),
            "expectancy_r": round(self.expectancy_r, 4),
            "sharpe": round(self.sharpe, 4),
            "sortino": round(self.sortino, 4),
            "initial_capital": self.initial_capital,
            "final_equity": round(self.final_equity, 2),
        }


class StrategyBacktester:
    """Bar-by-bar backtest engine for Strategy objects.

    Handles:
    - Pending orders (buy-stop, sell-stop) from signal entry levels
    - SL / TP exit logic checked on each bar's high/low
    - Indian cost model (brokerage, STT, exchange, SEBI, GST, stamp, slippage)
    - One position at a time (configurable)
    - Equity curve and trade log
    """

    def __init__(
        self,
        strategy: Strategy,
        df: pd.DataFrame,
        initial_capital: float = 100_000.0,
        slippage_pct: float = 0.0005,
        is_delivery: bool = False,
        cost_model: str = "indian",  # "indian" or "zero"
        max_open_positions: int = 1,
        progress_callback: Any = None,
    ):
        self.strategy = strategy
        self.df = df.copy()
        self.initial_capital = initial_capital
        self.slippage_pct = slippage_pct
        self.is_delivery = is_delivery
        self.cost_model = cost_model
        self.max_open_positions = max_open_positions
        self.progress_callback = progress_callback

    def run(self) -> StrategyBacktestResult:
        """Execute the bar-by-bar backtest."""
        strategy = self.strategy
        strategy.reset()

        # Pre-compute indicators
        df = strategy.compute_indicators(self.df)
        n = len(df)

        capital = self.initial_capital
        equity_curve = np.full(n, capital)
        trades: list[TradeRecord] = []
        pending_orders: list[dict[str, Any]] = []
        open_positions: list[dict[str, Any]] = []

        for bar_idx in range(n):
            high = df["high"].iloc[bar_idx]
            low = df["low"].iloc[bar_idx]
            close = df["close"].iloc[bar_idx]

            # ── 1. Check SL/TP on open positions ───────────────────────
            closed_positions = []
            for pos in open_positions:
                exit_price = None
                result = None

                if pos["direction"] == TradeDirection.LONG:
                    # Check SL first (worst case), then TP
                    if low <= pos["stop_loss"]:
                        exit_price = pos["stop_loss"]
                        result = "SL"
                    elif high >= pos["take_profit"]:
                        exit_price = pos["take_profit"]
                        result = "TP"
                elif pos["direction"] == TradeDirection.SHORT:
                    if high >= pos["stop_loss"]:
                        exit_price = pos["stop_loss"]
                        result = "SL"
                    elif low <= pos["take_profit"]:
                        exit_price = pos["take_profit"]
                        result = "TP"

                if exit_price is not None:
                    trade = self._close_position(pos, bar_idx, exit_price, result)
                    capital += trade.pnl_net
                    trades.append(trade)
                    closed_positions.append(pos)
                    strategy.on_exit(bar_idx, exit_price, result)

            for pos in closed_positions:
                open_positions.remove(pos)

            # ── 2. Check pending orders ────────────────────────────────
            filled_orders = []
            for order in pending_orders:
                if len(open_positions) >= self.max_open_positions:
                    break

                filled = False
                if order["direction"] == TradeDirection.LONG:
                    if high >= order["entry_price"]:
                        filled = True
                elif order["direction"] == TradeDirection.SHORT:
                    if low <= order["entry_price"]:
                        filled = True

                if filled:
                    entry_with_slip = self._apply_slippage(
                        order["entry_price"], order["direction"]
                    )
                    cost = self._compute_cost(
                        order["lots"], entry_with_slip, "BUY" if order["direction"] == TradeDirection.LONG else "SELL"
                    )
                    capital -= cost

                    pos = {
                        "entry_bar": bar_idx,
                        "direction": order["direction"],
                        "entry_price": entry_with_slip,
                        "stop_loss": order["stop_loss"],
                        "take_profit": order["take_profit"],
                        "lots": order["lots"],
                        "risk_per_trade": order["risk_per_trade"],
                        "entry_cost": cost,
                        "metadata": order.get("metadata", {}),
                    }
                    open_positions.append(pos)
                    filled_orders.append(order)
                    strategy.on_fill(bar_idx, entry_with_slip, order["direction"])

            for order in filled_orders:
                pending_orders.remove(order)

            # ── 3. Generate new signals ────────────────────────────────
            if len(open_positions) < self.max_open_positions:
                signals = strategy.generate_signals(df, bar_idx)
                for sig in signals:
                    lots = sig.lot_size(
                        min_lots=strategy.params.min_lots,
                        max_lots=strategy.params.max_lots,
                        point_value=strategy.params.point_value,
                    )
                    order = {
                        "direction": sig.direction,
                        "entry_price": sig.entry_price,
                        "stop_loss": sig.stop_loss,
                        "take_profit": sig.take_profit,
                        "lots": lots,
                        "risk_per_trade": sig.risk_per_trade,
                        "signal_bar": sig.bar_index,
                        "metadata": sig.metadata,
                    }
                    pending_orders.append(order)

            # ── 4. Mark-to-market equity ───────────────────────────────
            unrealized = 0.0
            for pos in open_positions:
                if pos["direction"] == TradeDirection.LONG:
                    unrealized += pos["lots"] * (close - pos["entry_price"])
                else:
                    unrealized += pos["lots"] * (pos["entry_price"] - close)

            equity_curve[bar_idx] = capital + unrealized

            # Progress callback
            if self.progress_callback and bar_idx % max(1, n // 20) == 0:
                self.progress_callback(int((bar_idx / n) * 100))

        # ── Close any remaining positions at last close ────────────────
        last_close = float(df["close"].iloc[-1])
        for pos in open_positions:
            trade = self._close_position(pos, n - 1, last_close, "END")
            capital += trade.pnl_net
            trades.append(trade)
        equity_curve[-1] = capital

        # ── Compute summary statistics ─────────────────────────────────
        return self._build_result(trades, equity_curve)

    def _close_position(
        self,
        pos: dict[str, Any],
        bar_idx: int,
        exit_price: float,
        result: str,
    ) -> TradeRecord:
        direction = pos["direction"]
        lots = pos["lots"]

        exit_with_slip = self._apply_slippage(
            exit_price,
            TradeDirection.SHORT if direction == TradeDirection.LONG else TradeDirection.LONG,
        )

        if direction == TradeDirection.LONG:
            pnl_gross = lots * (exit_with_slip - pos["entry_price"])
        else:
            pnl_gross = lots * (pos["entry_price"] - exit_with_slip)

        exit_cost = self._compute_cost(
            lots, exit_with_slip, "SELL" if direction == TradeDirection.LONG else "BUY"
        )
        total_cost = pos["entry_cost"] + exit_cost
        pnl_net = pnl_gross - exit_cost

        # R-multiple
        sl_dist = abs(pos["entry_price"] - pos["stop_loss"])
        r_multiple = 0.0
        if sl_dist > 0 and lots > 0:
            risk_amount = lots * sl_dist
            r_multiple = pnl_net / risk_amount if risk_amount > 0 else 0.0

        return TradeRecord(
            entry_bar=pos["entry_bar"],
            exit_bar=bar_idx,
            direction=direction.value,
            entry_price=pos["entry_price"],
            exit_price=exit_with_slip,
            stop_loss=pos["stop_loss"],
            take_profit=pos["take_profit"],
            lots=lots,
            pnl_gross=pnl_gross,
            cost=total_cost,
            pnl_net=pnl_net,
            result=result,
            risk_per_trade=pos["risk_per_trade"],
            r_multiple=r_multiple,
            metadata=pos.get("metadata", {}),
        )

    def _apply_slippage(self, price: float, direction: TradeDirection) -> float:
        if direction == TradeDirection.LONG:
            return price * (1 + self.slippage_pct)
        return price * (1 - self.slippage_pct)

    def _compute_cost(self, lots: float, price: float, side: str) -> float:
        if self.cost_model == "zero":
            return 0.0
        gross_value = lots * price
        breakdown = compute_indian_costs(
            gross_amount=gross_value,
            side=side,
            is_delivery=self.is_delivery,
            slippage_pct=0.0,  # already applied
        )
        return breakdown["total_cost"]

    def _build_result(
        self,
        trades: list[TradeRecord],
        equity_curve: np.ndarray,
    ) -> StrategyBacktestResult:
        total_trades = len(trades)

        if total_trades == 0:
            return StrategyBacktestResult(
                strategy_name=self.strategy.name,
                trades=trades,
                equity_curve=equity_curve,
                daily_returns=np.zeros_like(equity_curve),
                initial_capital=self.initial_capital,
                final_equity=float(equity_curve[-1]),
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                profit_factor=0.0,
                total_pnl_net=0.0,
                total_cost=0.0,
                max_drawdown=0.0,
                max_drawdown_duration=0,
                avg_r_multiple=0.0,
                expectancy_r=0.0,
                sharpe=0.0,
                sortino=0.0,
            )

        pnls = np.array([t.pnl_net for t in trades])
        r_multiples = np.array([t.r_multiple for t in trades])
        costs = np.array([t.cost for t in trades])

        winners = pnls[pnls > 0]
        losers = pnls[pnls <= 0]

        win_rate = len(winners) / total_trades if total_trades > 0 else 0.0
        gross_profit = float(np.sum(winners)) if len(winners) > 0 else 0.0
        gross_loss = float(np.abs(np.sum(losers))) if len(losers) > 0 else 0.0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Daily returns from equity curve
        daily_returns = np.zeros_like(equity_curve)
        daily_returns[1:] = np.diff(equity_curve) / np.where(
            equity_curve[:-1] == 0, np.nan, equity_curve[:-1]
        )
        daily_returns = np.nan_to_num(daily_returns, nan=0.0)

        # Max drawdown
        running_max = np.maximum.accumulate(equity_curve)
        drawdown = equity_curve / running_max - 1.0
        max_dd = float(np.min(drawdown))

        dd_duration = 0
        current = 0
        for dd in drawdown:
            if dd < 0:
                current += 1
                dd_duration = max(dd_duration, current)
            else:
                current = 0

        # Sharpe and Sortino
        excess = daily_returns
        sigma = float(np.std(excess, ddof=1))
        sharpe = float(np.mean(excess) / sigma * np.sqrt(252.0)) if sigma > 0 else 0.0

        downside = np.minimum(excess, 0.0)
        downside_std = float(np.std(downside, ddof=1))
        sortino = float(np.mean(excess) / downside_std * np.sqrt(252.0)) if downside_std > 0 else 0.0

        return StrategyBacktestResult(
            strategy_name=self.strategy.name,
            trades=trades,
            equity_curve=equity_curve,
            daily_returns=daily_returns,
            initial_capital=self.initial_capital,
            final_equity=float(equity_curve[-1]),
            total_trades=total_trades,
            winning_trades=int(len(winners)),
            losing_trades=int(len(losers)),
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_pnl_net=float(np.sum(pnls)),
            total_cost=float(np.sum(costs)),
            max_drawdown=max_dd,
            max_drawdown_duration=dd_duration,
            avg_r_multiple=float(np.mean(r_multiples)),
            expectancy_r=float(np.mean(r_multiples)),
            sharpe=sharpe,
            sortino=sortino,
        )
