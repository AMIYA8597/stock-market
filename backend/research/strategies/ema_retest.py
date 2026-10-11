"""EMA 50 Retest Strategy.

Ported from the TradingView Pine Script "ema_retest.pine" (462+ lines).

A retest is defined as:
  1. Price touches EMA 50 (within ``touch_tolerance`` * ATR)
  2. Price moves away by at least ``move_away_atr`` * ATR
  3. Price returns to touch EMA 50 again (bounce candle within ``max_bounce_bars``)

Entry on the bounce candle's break (high for LONG, low for SHORT).

Filters (all optional, toggled via params):
  - Higher-timeframe EMA 50 trend confirmation (slope > 0 for LONG)
  - ADX > threshold
  - EMA slope direction filter
  - Break-of-both-EMAs rule (price must have crossed both 9 and 21 before retest)

Risk management:
  - SL = swing low/high of ``sl_lookback`` bars ± ATR buffer
  - TP = ``reward_risk`` * SL distance (default 3R)
  - Fixed risk per trade (default $40 / ₹40)
  - One trade at a time
  - Stats tracked by retest number (1st, 2nd, 3rd, etc.)
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from research.strategies.base import Strategy, StrategySignal, TradeDirection

logger = logging.getLogger(__name__)


class EMARetestStrategy(Strategy):
    """EMA 50 retest bounce strategy."""

    name = "ema_retest"
    description = (
        "Detects retests of the EMA 50 level using ATR-based touch tolerance. "
        "Enters on the bounce candle break with optional higher-timeframe trend, "
        "ADX, and slope filters.  Tracks stats by retest number."
    )
    version = "1.0.0"

    @classmethod
    def default_params(cls) -> dict[str, Any]:
        return {
            "ema_length": 50,
            "touch_tolerance_atr": 0.3,   # within 0.3*ATR = "touched"
            "move_away_atr": 1.0,         # must move 1*ATR away for new retest
            "max_bounce_bars": 3,          # bounce must happen within N bars of touch
            "reward_risk": 3.0,
            "sl_lookback": 3,
            "sl_atr_buffer": 0.1,
            "min_sl_atr_mult": 0.3,
            "risk_per_trade": 40.0,
            "min_lots": 0.01,
            "max_lots": 10.0,
            "point_value": 1.0,
            # Filters
            "use_slope_filter": True,
            "slope_lookback": 5,           # bars to measure EMA slope
            "use_htf_filter": False,        # higher-timeframe EMA 50 confirmation
            "htf_ema_col": "ema_50_htf",   # column name if pre-computed
            "use_adx_filter": False,
            "adx_threshold": 20.0,
            "use_break_both_emas": False,   # price must have broken both 9 & 21
            "ema_fast": 9,
            "ema_slow": 21,
            "allow_long": True,
            "allow_short": True,
            "max_retests": 0,               # 0 = no limit
        }

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Pre-compute EMA 50, ATR, and optional filters."""
        data = df.copy()
        p = self.params

        # EMA 50
        if "ema_50" not in data.columns:
            data["ema_50"] = data["close"].ewm(span=p.ema_length, adjust=False).mean()

        # ATR 14
        if "atr_14" not in data.columns:
            data["atr_14"] = _compute_atr(data, 14)

        # EMA 9 and 21 (for break-of-both filter)
        if p.use_break_both_emas:
            if "ema_9" not in data.columns:
                data["ema_9"] = data["close"].ewm(span=p.ema_fast, adjust=False).mean()
            if "ema_21" not in data.columns:
                data["ema_21"] = data["close"].ewm(span=p.ema_slow, adjust=False).mean()

        # ADX
        if p.use_adx_filter and "adx_14" not in data.columns:
            adx_df = _compute_adx(data, 14)
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
        """Detect EMA 50 retest bounces."""
        p = self.params
        warmup = max(p.ema_length, 30) + 5
        if bar_index < warmup:
            return []

        close = df["close"].iloc[bar_index]
        high = df["high"].iloc[bar_index]
        low = df["low"].iloc[bar_index]
        ema = df["ema_50"].iloc[bar_index]
        atr = df["atr_14"].iloc[bar_index]

        if np.isnan(ema) or np.isnan(atr) or atr <= 0:
            return []

        signals: list[StrategySignal] = []
        in_trade = self._state.get("in_trade", False)
        if in_trade:
            return []

        # ── Track retest state ──────────────────────────────────────────
        # State machine: IDLE → TOUCHED → MOVED_AWAY → BOUNCE_WATCH
        phase = self._state.get("phase", "IDLE")
        touch_tol = p.touch_tolerance_atr * atr
        move_away_dist = p.move_away_atr * atr

        # Detect touch (price within tolerance of EMA)
        is_touching = abs(close - ema) <= touch_tol or _bar_crosses_ema(high, low, ema)

        # Distance from EMA
        dist_from_ema = close - ema  # positive = above, negative = below

        if phase == "IDLE":
            if is_touching:
                self._state["phase"] = "TOUCHED"
                self._state["touch_bar"] = bar_index
                self._state["touch_side"] = "ABOVE" if dist_from_ema > 0 else "BELOW"
            return []

        elif phase == "TOUCHED":
            # Wait for price to move away
            if abs(dist_from_ema) >= move_away_dist:
                self._state["phase"] = "MOVED_AWAY"
                self._state["away_side"] = "ABOVE" if dist_from_ema > 0 else "BELOW"
                self._state["max_dist"] = abs(dist_from_ema)
            elif is_touching:
                # Still touching, update touch bar
                self._state["touch_bar"] = bar_index
            return []

        elif phase == "MOVED_AWAY":
            # Track max distance
            current_dist = abs(dist_from_ema)
            max_dist = self._state.get("max_dist", 0)
            if current_dist > max_dist:
                self._state["max_dist"] = current_dist

            # Check for retest (return to EMA)
            if is_touching:
                self._state["phase"] = "BOUNCE_WATCH"
                self._state["retest_bar"] = bar_index
                retest_num = self._state.get("retest_count", 0) + 1
                self._state["retest_count"] = retest_num

                # Check max retests
                if p.max_retests > 0 and retest_num > p.max_retests:
                    self._state["phase"] = "IDLE"
                    return []
            return []

        elif phase == "BOUNCE_WATCH":
            retest_bar = self._state.get("retest_bar", bar_index)
            bars_since_retest = bar_index - retest_bar

            if bars_since_retest > p.max_bounce_bars:
                # No bounce within window — go back to TOUCHED
                self._state["phase"] = "TOUCHED"
                self._state["touch_bar"] = bar_index
                return []

            # Determine direction based on which side price moved away to
            away_side = self._state.get("away_side", "ABOVE")

            if away_side == "ABOVE":
                # Price was above EMA, came back to retest → LONG (bounce up)
                direction = TradeDirection.LONG
            else:
                direction = TradeDirection.SHORT

            # Check if this is a bounce candle
            is_bounce = False
            if direction == TradeDirection.LONG and p.allow_long:
                # Bounce up: close above EMA and bullish candle
                if close > ema and close > df["open"].iloc[bar_index]:
                    is_bounce = True
            elif direction == TradeDirection.SHORT and p.allow_short:
                # Bounce down: close below EMA and bearish candle
                if close < ema and close < df["open"].iloc[bar_index]:
                    is_bounce = True

            if not is_bounce:
                return []

            # ── Apply filters ───────────────────────────────────────────
            if not self._pass_filters(df, bar_index, direction):
                return []

            # ── Calculate entry, SL, TP ─────────────────────────────────
            retest_num = self._state.get("retest_count", 1)

            if direction == TradeDirection.LONG:
                entry = float(high)  # break of bounce candle high
                sl = self._calc_sl_long(df, bar_index, atr)
                sl_dist = entry - sl
                if sl_dist <= 0:
                    self._state["phase"] = "IDLE"
                    return []
                tp = entry + p.reward_risk * sl_dist
            else:
                entry = float(low)
                sl = self._calc_sl_short(df, bar_index, atr)
                sl_dist = sl - entry
                if sl_dist <= 0:
                    self._state["phase"] = "IDLE"
                    return []
                tp = entry - p.reward_risk * sl_dist

            sig = StrategySignal(
                bar_index=bar_index,
                direction=direction,
                entry_price=entry,
                stop_loss=sl,
                take_profit=tp,
                risk_per_trade=p.risk_per_trade,
                metadata={
                    "strategy": self.name,
                    "trigger": "ema_retest_bounce",
                    "retest_number": retest_num,
                    "away_side": away_side,
                    "bars_since_retest": bars_since_retest,
                    "atr": float(atr),
                    "ema_50": float(ema),
                },
            )
            signals.append(sig)
            self._state["in_trade"] = True
            self._state["phase"] = "IDLE"
            return signals

        return []

    def on_exit(self, bar_index: int, exit_price: float, result: str) -> None:
        self._state["in_trade"] = False

    # ── Filter helpers ──────────────────────────────────────────────────

    def _pass_filters(
        self,
        df: pd.DataFrame,
        bar_index: int,
        direction: TradeDirection,
    ) -> bool:
        p = self.params

        # Slope filter
        if p.use_slope_filter:
            lookback = min(p.slope_lookback, bar_index)
            if lookback < 2:
                return False
            ema_now = df["ema_50"].iloc[bar_index]
            ema_prev = df["ema_50"].iloc[bar_index - lookback]
            slope = ema_now - ema_prev
            if direction == TradeDirection.LONG and slope <= 0:
                return False
            if direction == TradeDirection.SHORT and slope >= 0:
                return False

        # Higher-timeframe filter
        if p.use_htf_filter:
            htf_col = p.htf_ema_col
            if htf_col in df.columns:
                htf_ema = df[htf_col].iloc[bar_index]
                if not np.isnan(htf_ema):
                    close = df["close"].iloc[bar_index]
                    if direction == TradeDirection.LONG and close < htf_ema:
                        return False
                    if direction == TradeDirection.SHORT and close > htf_ema:
                        return False

        # ADX filter
        if p.use_adx_filter:
            adx = df["adx_14"].iloc[bar_index]
            if np.isnan(adx) or adx < p.adx_threshold:
                return False

        # Break-of-both-EMAs filter
        if p.use_break_both_emas:
            if "ema_9" in df.columns and "ema_21" in df.columns:
                close = df["close"].iloc[bar_index]
                ema_9 = df["ema_9"].iloc[bar_index]
                ema_21 = df["ema_21"].iloc[bar_index]
                if direction == TradeDirection.LONG:
                    if not (close > ema_9 and close > ema_21):
                        return False
                else:
                    if not (close < ema_9 and close < ema_21):
                        return False

        return True

    # ── SL helpers ──────────────────────────────────────────────────────

    def _calc_sl_long(self, df: pd.DataFrame, bar_index: int, atr: float) -> float:
        lookback = self.params.sl_lookback
        start = max(0, bar_index - lookback + 1)
        lowest = float(df["low"].iloc[start : bar_index + 1].min())
        sl = lowest - self.params.sl_atr_buffer * atr
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


# ── Helpers ──────────────────────────────────────────────────────────────


def _bar_crosses_ema(high: float, low: float, ema: float) -> bool:
    """True if the bar's range straddles the EMA."""
    return low <= ema <= high


def _compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
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

    alpha = 1.0 / period
    atr_arr = np.zeros(n)
    dmp_smooth = np.zeros(n)
    dmn_smooth = np.zeros(n)

    if n > period:
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
