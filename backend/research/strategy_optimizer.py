"""Grid-search optimizer for TradingView strategies.

Usage:
    cd backend && uv run python research/strategy_optimizer.py --symbol RELIANCE.NS --period 2y
"""

from __future__ import annotations

import argparse
import itertools
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("research.strategy_optimizer")


@dataclass
class StrategyResult:
    params: dict[str, float]
    total_return: float
    sharpe: float
    max_drawdown: float
    win_rate: float
    n_trades: int
    profit_factor: float


def _compute_metrics(trades: list[float]) -> dict[str, float]:
    if not trades:
        return {"total_return": 0.0, "sharpe": 0.0, "max_drawdown": 0.0,
                "win_rate": 0.0, "n_trades": 0, "profit_factor": 0.0}

    arr = np.array(trades)
    total_ret = float(np.sum(arr))
    wins = arr[arr > 0]
    losses = arr[arr < 0]
    win_rate = float(len(wins) / len(arr)) if len(arr) > 0 else 0.0
    gross_profit = float(np.sum(wins)) if len(wins) > 0 else 0.0
    gross_loss = float(np.abs(np.sum(losses))) if len(losses) > 0 else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

    cum = np.cumsum(arr)
    peak = np.maximum.accumulate(cum)
    dd = cum - peak
    max_dd = float(np.min(dd)) if len(dd) > 0 else 0.0

    mean_r = float(np.mean(arr))
    std_r = float(np.std(arr))
    sharpe = float(np.sqrt(252) * mean_r / std_r) if std_r > 0 else 0.0

    return {"total_return": total_ret, "sharpe": sharpe, "max_drawdown": max_dd,
            "win_rate": win_rate, "n_trades": len(arr), "profit_factor": profit_factor}


def run_ema_cross_vwap_adx_backtest(
    df: pd.DataFrame,
    ema_fast: int = 9,
    ema_slow: int = 21,
    adx_threshold: float = 20.0,
    reward_risk: float = 3.0,
) -> StrategyResult:
    import pandas_ta as ta

    data = df.copy()
    data["ema_fast"] = ta.ema(data["close"], length=ema_fast)
    data["ema_slow"] = ta.ema(data["close"], length=ema_slow)
    adx_df = ta.adx(data["high"], data["low"], data["close"], length=14)
    data["adx"] = adx_df["ADX_14"]
    # Daily-resetting VWAP for intraday data
    date_groups = data.index.date
    typical = (data["high"] + data["low"] + data["close"]) / 3
    data["vwap"] = (typical * data["volume"]).groupby(date_groups).cumsum() / data["volume"].groupby(date_groups).cumsum()
    data["atr"] = ta.atr(data["high"], data["low"], data["close"], length=14)
    data = data.dropna()

    trades: list[float] = []
    position = 0
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0

    for _i, row in data.iterrows():
        if position == 0:
            if (row["ema_fast"] > row["ema_slow"]
                    and row["close"] > row["vwap"]
                    and row["adx"] > adx_threshold):
                position = 1
                entry_price = row["close"]
                atr = row["atr"]
                stop_loss = entry_price - 1.5 * atr
                take_profit = entry_price + reward_risk * 1.5 * atr
            elif (row["ema_fast"] < row["ema_slow"]
                  and row["close"] < row["vwap"]
                  and row["adx"] > adx_threshold):
                position = -1
                entry_price = row["close"]
                atr = row["atr"]
                stop_loss = entry_price + 1.5 * atr
                take_profit = entry_price - reward_risk * 1.5 * atr
        elif position == 1:
            if row["low"] <= stop_loss or row["high"] >= take_profit:
                exit_price = take_profit if row["high"] >= take_profit else stop_loss
                trades.append((exit_price - entry_price) / entry_price)
                position = 0
        elif position == -1:
            if row["high"] >= stop_loss or row["low"] <= take_profit:
                exit_price = take_profit if row["low"] <= take_profit else stop_loss
                trades.append((entry_price - exit_price) / entry_price)
                position = 0

    metrics = _compute_metrics(trades)
    params = {"ema_fast": ema_fast, "ema_slow": ema_slow,
              "adx_threshold": adx_threshold, "reward_risk": reward_risk}
    return StrategyResult(params=params, **metrics)


def run_ema_retest_backtest(
    df: pd.DataFrame,
    ema_length: int = 50,
    touch_tolerance_atr: float = 0.3,
    move_away_atr: float = 1.0,
    reward_risk: float = 3.0,
) -> StrategyResult:
    import pandas_ta as ta

    data = df.copy()
    data["ema"] = ta.ema(data["close"], length=ema_length)
    data["atr"] = ta.atr(data["high"], data["low"], data["close"], length=14)
    data = data.dropna()

    trades: list[float] = []
    position = 0
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    state = "waiting"
    retest_count = 0

    for _i, row in data.iterrows():
        atr_val = row["atr"]

        if position == 0:
            if state == "waiting":
                if abs(row["close"] - row["ema"]) < touch_tolerance_atr * atr_val:
                    state = "touched"
            elif state == "touched":
                if row["close"] > row["ema"] + move_away_atr * atr_val:
                    state = "moved_up"
                    retest_count = 0
                elif row["close"] < row["ema"] - move_away_atr * atr_val:
                    state = "moved_down"
                    retest_count = 0
                elif abs(row["close"] - row["ema"]) > 2 * move_away_atr * atr_val:
                    state = "waiting"
            elif state == "moved_up":
                if abs(row["low"] - row["ema"]) < touch_tolerance_atr * atr_val and retest_count < 2:
                    position = 1
                    entry_price = row["close"]
                    stop_loss = entry_price - 1.5 * atr_val
                    take_profit = entry_price + reward_risk * 1.5 * atr_val
                    retest_count += 1
                    state = "waiting"
                elif row["close"] < row["ema"] - move_away_atr * atr_val:
                    state = "waiting"
            elif state == "moved_down":
                if abs(row["high"] - row["ema"]) < touch_tolerance_atr * atr_val and retest_count < 2:
                    position = -1
                    entry_price = row["close"]
                    stop_loss = entry_price + 1.5 * atr_val
                    take_profit = entry_price - reward_risk * 1.5 * atr_val
                    retest_count += 1
                    state = "waiting"
                elif row["close"] > row["ema"] + move_away_atr * atr_val:
                    state = "waiting"
        elif position == 1:
            if row["low"] <= stop_loss or row["high"] >= take_profit:
                exit_price = take_profit if row["high"] >= take_profit else stop_loss
                trades.append((exit_price - entry_price) / entry_price)
                position = 0
        elif position == -1:
            if row["high"] >= stop_loss or row["low"] <= take_profit:
                exit_price = take_profit if row["low"] <= take_profit else stop_loss
                trades.append((entry_price - exit_price) / entry_price)
                position = 0

    metrics = _compute_metrics(trades)
    params = {"ema_length": ema_length, "touch_tolerance_atr": touch_tolerance_atr,
              "move_away_atr": move_away_atr, "reward_risk": reward_risk}
    return StrategyResult(params=params, **metrics)


def optimize_ema_cross_vwap_adx(df: pd.DataFrame) -> list[StrategyResult]:
    grid = {
        "ema_fast": [5, 9, 13],
        "ema_slow": [15, 21, 30],
        "adx_threshold": [15.0, 20.0, 25.0],
        "reward_risk": [2.0, 3.0, 4.0],
    }
    keys = list(grid.keys())
    values = list(grid.values())
    results: list[StrategyResult] = []

    total = 1
    for v in values:
        total *= len(v)
    logger.info("Running %d EMA Cross VWAP ADX combinations", total)

    for combo in itertools.product(*values):
        params = dict(zip(keys, combo, strict=True))
        if params["ema_fast"] >= params["ema_slow"]:
            continue
        result = run_ema_cross_vwap_adx_backtest(df, **params)
        results.append(result)

    results.sort(key=lambda r: r.sharpe, reverse=True)
    return results


def optimize_ema_retest(df: pd.DataFrame) -> list[StrategyResult]:
    grid = {
        "ema_length": [30, 50, 100],
        "touch_tolerance_atr": [0.2, 0.3, 0.5],
        "move_away_atr": [0.5, 1.0, 1.5],
        "reward_risk": [2.0, 3.0, 4.0],
    }
    keys = list(grid.keys())
    values = list(grid.values())
    results: list[StrategyResult] = []

    total = 1
    for v in values:
        total *= len(v)
    logger.info("Running %d EMA Retest combinations", total)

    for combo in itertools.product(*values):
        params = dict(zip(keys, combo, strict=True))
        result = run_ema_retest_backtest(df, **params)
        results.append(result)

    results.sort(key=lambda r: r.sharpe, reverse=True)
    return results


def print_optimization_results(name: str, results: list[StrategyResult], top_n: int = 5) -> None:
    sep = "=" * 80
    print(f"\n{sep}")
    print(f"OPTIMIZATION RESULTS: {name}")
    print(f"Date: {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(f"Total combinations tested: {len(results)}")
    print(sep)

    for i, r in enumerate(results[:top_n]):
        print(f"\n  Rank {i+1}:")
        print(f"    Params: {r.params}")
        print(f"    Sharpe: {r.sharpe:.3f}")
        print(f"    Total Return: {r.total_return:.4f}")
        print(f"    Max Drawdown: {r.max_drawdown:.4f}")
        print(f"    Win Rate: {r.win_rate:.4f}")
        print(f"    Trades: {r.n_trades}")
        print(f"    Profit Factor: {r.profit_factor:.3f}")

    print(f"\n{sep}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Strategy Optimizer")
    parser.add_argument("--symbol", default="RELIANCE.NS")
    parser.add_argument("--period", default="2y")
    parser.add_argument("--interval", default="1h")
    args = parser.parse_args()

    import yfinance as yf

    logger.info("Fetching %s %s data for %s", args.period, args.interval, args.symbol)
    ticker = yf.Ticker(args.symbol)
    df = ticker.history(period=args.period, interval=args.interval)

    if df.empty:
        logger.error("No data returned for %s", args.symbol)
        return

    df.index = pd.DatetimeIndex(df.index).tz_localize(None)
    df = df.rename(columns={
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Volume": "volume",
    })
    df = df[["open", "high", "low", "close", "volume"]].dropna()
    logger.info("Fetched %d bars", len(df))

    cross_results = optimize_ema_cross_vwap_adx(df)
    print_optimization_results("EMA Cross VWAP ADX", cross_results)

    retest_results = optimize_ema_retest(df)
    print_optimization_results("EMA Retest", retest_results)


if __name__ == "__main__":
    main()
