"""EMA 9/21 Crossover + VWAP + ADX Strategy.

Ported from the TradingView Pine Script "ema_cross_vwap_adx.pine".

LONG signal candle:
  - EMA(9) crosses above EMA(21)
  - Both EMAs are above session VWAP (daily-anchored)
  - ADX(14) > 20 on that candle

Entry:
  - Buy-stop one tick above the signal candle's high
  - If not hit next bar, move the stop to each newly closed candle's high
    until filled or the opposite crossover cancels the setup

SL:
  - Lowest low of last ``sl_lookback`` bars minus 0.1 * ATR(14)
  - Minimum SL distance = 0.3 * ATR(14)

TP:
  - ``reward_risk`` * SL distance (default 3R)

Position sizing:
  - Fixed risk per trade (default ₹40 / $40)
  - One trade at a time

SHORT is the exact mirror.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from research.strategies.base import Strategy, StrategySignal, TradeDirection

logger = logging.getLogger(__name__)


class EMACrossVWAPADXStrategy(Strategy):
    """EMA 9/21 crossover filtered by VWAP and ADX."""

    name = "ema_cross_vwap_adx"
    description = (
        "EMA 9/21 crossover with VWAP trend confirmation and ADX > 20 filter. "
        "Entry on break of signal candle high/low; SL = swing low/high minus ATR buffer; "
        "TP = 3R.  One trade at a time."
    )
    version = "1.0.0"

    @classmethod
    def default_params(cls) -> dict[str, Any]:
        return {
            "ema_fast": 9,
            "ema_slow": 21,
            "adx_length": 14,
            "adx_threshold": 20.0,
            "require_di_direction": False,
            "reward_risk": 3.0,
            "sl_lookback": 3,
            "sl_atr_buffer": 0.1,
            "min_sl_atr_mult": 0.3,
            "risk_per_trade": 40.0,
            "min_lots": 0.01,
            "max_lots": 10.0,
            "point_value": 1.0,  # 1 for equities, 100 for XAUUSD
            "max_wait_bars": 0,  # 0 = wait until opposite crossover
            "allow_long": True,
            "allow_short": True,
        }

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Pre-compute EMA, VWAP, ADX, ATR."""
        data = df.copy()
        fast = self.params.ema_fast
        slow = self.params.ema_slow
        adx_len = self.params.adx_length

        # EMAs
        data["ema_fast"] = data["close"].ewm(span=fast, adjust=False).mean()
        data["ema_slow"] = data["close"].ewm(span=slow, adjust=False).mean()

        # VWAP (session-anchored, daily reset)
        if "vwap" not in data.columns:
            data["vwap"] = _compute_vwap(data)

        # ATR
        if "atr_14" not in data.columns:
            data["atr_14"] = _compute_atr(data, adx_len)

        # ADX + DI
        if "adx_14" not in data.columns:
            adx_df = _compute_adx(data, adx_len)
            data["adx_14"] = adx_df["adx"]
            data["dmp_14"] = adx_df["dmp"]
            data["dmn_14"] = adx_df["dmn"]

        return data

    def reset(self) -> None:
        super().reset()
        self._state.clear()

    def generate_signals(
        self,
        df: pd.DataFrame,
        bar_index: int,
    ) -> list[StrategySignal]:
        """Check for crossover signals at bar_index."""
        if bar_index < max(self.params.ema_slow, self.params.adx_length) + 2:
            return []

        p = self.params
        signals: list[StrategySignal] = []

        # Current and previous values
        ema_f = df["ema_fast"].iloc[bar_index]
        ema_s = df["ema_slow"].iloc[bar_index]
        ema_f_prev = df["ema_fast"].iloc[bar_index - 1]
        ema_s_prev = df["ema_slow"].iloc[bar_index - 1]
        vwap = df["vwap"].iloc[bar_index]
        adx = df["adx_14"].iloc[bar_index]
        atr = df["atr_14"].iloc[bar_index]

        if np.isnan(ema_f) or np.isnan(ema_s) or np.isnan(adx) or np.isnan(atr) or atr <= 0:
            return []

        # Pending setup management
        pending = self._state.get("pending")
        in_trade = self._state.get("in_trade", False)

        if in_trade:
            return []  # one trade at a time

        # Check if pending setup was filled or cancelled
        if pending is not None:
            direction = pending["direction"]
            entry_level = pending["entry_price"]
            bars_waited = bar_index - pending["signal_bar"]

            # Cancel on opposite crossover
            if direction == TradeDirection.LONG and ema_f < ema_s:
                self._state.pop("pending", None)
                pending = None
            elif direction == TradeDirection.SHORT and ema_f > ema_s:
                self._state.pop("pending", None)
                pending = None
            # Cancel on max wait
            elif p.max_wait_bars > 0 and bars_waited > p.max_wait_bars:
                self._state.pop("pending", None)
                pending = None
            else:
                # Check if entry level was hit this bar
                high = df["high"].iloc[bar_index]
                low = df["low"].iloc[bar_index]

                if direction == TradeDirection.LONG and high >= entry_level:
                    # Filled! Recalculate SL from current bars
                    sl = self._calc_sl_long(df, bar_index, atr)
                    sl_dist = entry_level - sl
                    if sl_dist <= 0:
                        self._state.pop("pending", None)
                        return []
                    tp = entry_level + p.reward_risk * sl_dist

                    sig = StrategySignal(
                        bar_index=bar_index,
                        direction=TradeDirection.LONG,
                        entry_price=entry_level,
                        stop_loss=sl,
                        take_profit=tp,
                        risk_per_trade=p.risk_per_trade,
                        metadata={
                            "strategy": self.name,
                            "trigger": "breakout_fill",
                            "wait_bars": bars_waited,
                            "adx": float(adx),
                            "atr": float(atr),
                        },
                    )
                    signals.append(sig)
                    self._state["in_trade"] = True
                    self._state.pop("pending", None)
                    return signals

                elif direction == TradeDirection.SHORT and low <= entry_level:
                    sl = self._calc_sl_short(df, bar_index, atr)
                    sl_dist = sl - entry_level
                    if sl_dist <= 0:
                        self._state.pop("pending", None)
                        return []
                    tp = entry_level - p.reward_risk * sl_dist

                    sig = StrategySignal(
                        bar_index=bar_index,
                        direction=TradeDirection.SHORT,
                        entry_price=entry_level,
                        stop_loss=sl,
                        take_profit=tp,
                        risk_per_trade=p.risk_per_trade,
                        metadata={
                            "strategy": self.name,
                            "trigger": "breakout_fill",
                            "wait_bars": bars_waited,
                            "adx": float(adx),
                            "atr": float(atr),
                        },
                    )
                    signals.append(sig)
                    self._state["in_trade"] = True
                    self._state.pop("pending", None)
                    return signals
                else:
                    # Move entry level to current bar's high/low
                    if direction == TradeDirection.LONG:
                        pending["entry_price"] = float(df["high"].iloc[bar_index])
                    else:
                        pending["entry_price"] = float(df["low"].iloc[bar_index])

            return signals  # still pending, no new signal

        # ── Detect new crossover ────────────────────────────────────────
        # LONG crossover: ema_fast crosses above ema_slow
        long_cross = (ema_f_prev <= ema_s_prev) and (ema_f > ema_s)
        # SHORT crossover: ema_fast crosses below ema_slow
        short_cross = (ema_f_prev >= ema_s_prev) and (ema_f < ema_s)

        if long_cross and p.allow_long:
            # Both EMAs above VWAP
            if ema_f > vwap and ema_s > vwap and adx >= p.adx_threshold:
                if p.require_di_direction:
                    dmp = df["dmp_14"].iloc[bar_index]
                    dmn = df["dmn_14"].iloc[bar_index]
                    if not (dmp > dmn):
                        return []

                # Signal candle = current bar; entry = break of its high
                entry = float(df["high"].iloc[bar_index])
                self._state["pending"] = {
                    "direction": TradeDirection.LONG,
                    "entry_price": entry,
                    "signal_bar": bar_index,
                }

        elif short_cross and p.allow_short:
            if ema_f < vwap and ema_s < vwap and adx >= p.adx_threshold:
                if p.require_di_direction:
                    dmp = df["dmp_14"].iloc[bar_index]
                    dmn = df["dmn_14"].iloc[bar_index]
                    if not (dmn > dmp):
                        return []

                entry = float(df["low"].iloc[bar_index])
                self._state["pending"] = {
                    "direction": TradeDirection.SHORT,
                    "entry_price": entry,
                    "signal_bar": bar_index,
                }

        return signals

    def on_exit(self, bar_index: int, exit_price: float, result: str) -> None:
        self._state["in_trade"] = False

    # ── SL helpers ──────────────────────────────────────────────────────

    def _calc_sl_long(self, df: pd.DataFrame, bar_index: int, atr: float) -> float:
        lookback = self.params.sl_lookback
        start = max(0, bar_index - lookback + 1)
        lowest = float(df["low"].iloc[start : bar_index + 1].min())
        sl = lowest - self.params.sl_atr_buffer * atr
        # Ensure minimum SL distance
        entry = float(df["high"].iloc[bar_index])
        min_dist = self.params.min_sl_atr_mult * atr
        if entry - sl < min_dist:
            sl = entry - min_dist
        return sl

    def _calc_sl_short(self, df: pd.DataFrame, bar_index: int, atr: float) -> float:
        lookback = self.params.sl_lookback
        start = max(0, bar_index - lookback + 1)
        highest = float(df["high"].iloc[start : bar_index + 1].max())
        sl = highest + self.params.sl_atr_buffer * atr
        entry = float(df["low"].iloc[bar_index])
        min_dist = self.params.min_sl_atr_mult * atr
        if sl - entry < min_dist:
            sl = entry + min_dist
        return sl


# ── Indicator helpers (no look-ahead) ────────────────────────────────────


def _compute_vwap(df: pd.DataFrame) -> pd.Series:
    """Session-anchored VWAP resetting at each trading day boundary."""
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    vol = df["volume"].replace(0, np.nan)

    # Detect session boundaries (date changes)
    if "time" in df.columns:
        dates = pd.to_datetime(df["time"]).dt.date
    elif isinstance(df.index, pd.DatetimeIndex):
        dates = df.index.date
    else:
        # Fallback: continuous VWAP (no daily reset)
        cum_pv = (typical * vol).cumsum()
        cum_v = vol.cumsum()
        return cum_pv / cum_v

    # Convert to pandas Series for shift/groupby (dates may be numpy array)
    dates_s = pd.Series(dates, index=df.index)
    session_start = dates_s != dates_s.shift(1)
    group_id = session_start.cumsum()
    cum_pv = (typical * vol).groupby(group_id).cumsum()
    cum_v = vol.groupby(group_id).cumsum()
    return cum_pv / cum_v


def _compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range."""
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


def _compute_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """ADX, +DI, -DI using Wilder's smoothing."""
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    n = len(high)

    tr = np.zeros(n)
    dm_plus = np.zeros(n)
    dm_minus = np.zeros(n)

    for i in range(1, n):
        h_diff = high[i] - high[i - 1]
        l_diff = low[i - 1] - low[i]
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
        dm_plus[i] = h_diff if (h_diff > l_diff and h_diff > 0) else 0.0
        dm_minus[i] = l_diff if (l_diff > h_diff and l_diff > 0) else 0.0

    # Wilder's smoothing
    alpha = 1.0 / period
    atr_arr = np.zeros(n)
    dmp_smooth = np.zeros(n)
    dmn_smooth = np.zeros(n)

    atr_arr[period] = np.mean(tr[1 : period + 1])
    dmp_smooth[period] = np.mean(dm_plus[1 : period + 1])
    dmn_smooth[period] = np.mean(dm_minus[1 : period + 1])

    for i in range(period + 1, n):
        atr_arr[i] = atr_arr[i - 1] * (1 - alpha) + tr[i] * alpha
        dmp_smooth[i] = dmp_smooth[i - 1] * (1 - alpha) + dm_plus[i] * alpha
        dmn_smooth[i] = dmn_smooth[i - 1] * (1 - alpha) + dm_minus[i] * alpha

    di_plus = np.where(atr_arr > 0, 100.0 * dmp_smooth / atr_arr, 0.0)
    di_minus = np.where(atr_arr > 0, 100.0 * dmn_smooth / atr_arr, 0.0)

    dx = np.where(
        (di_plus + di_minus) > 0,
        100.0 * np.abs(di_plus - di_minus) / (di_plus + di_minus),
        0.0,
    )

    adx = np.zeros(n)
    start = 2 * period
    if start < n:
        adx[start] = np.mean(dx[period : start + 1])
        for i in range(start + 1, n):
            adx[i] = adx[i - 1] * (1 - alpha) + dx[i] * alpha

    result = pd.DataFrame(index=df.index)
    result["adx"] = adx
    result["dmp"] = di_plus
    result["dmn"] = di_minus
    return result
