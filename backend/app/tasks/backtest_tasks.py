"""Celery tasks for executing backtest jobs."""

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

import numpy as np
from celery import shared_task
from sqlalchemy import select

from app.database.connection import async_session_factory
from app.models.backtest import BacktestJob
from app.services.market_data_service import MarketDataService
from app.websocket.connection_manager import get_connection_manager

ws_manager = get_connection_manager()
from research.backtesting.analytics import (
    cagr,
    calculate_turnover,
    calmar_ratio,
    max_drawdown,
    sharpe_ratio,
    sortino_ratio,
    trade_metrics,
)
from research.backtesting.engine import EventDrivenBacktester

logger = logging.getLogger(__name__)


async def run_backtest_async(job_id: str) -> None:
    """Async execution of the backtest job."""
    async with async_session_factory() as db:
        stmt = select(BacktestJob).where(BacktestJob.id == UUID(job_id))
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()

        if not job:
            logger.error(f"BacktestJob {job_id} not found.")
            return

        try:
            # 1. Start Job
            job.status = "RUNNING"
            await db.commit()
            await ws_manager.broadcast(
                "signals:backtest-progress", {"job_id": job_id, "status": "RUNNING", "progress": 0}
            )

            # 2. Fetch history (just using first symbol for now)
            symbol = job.universe[0]
            import pandas as pd

            # Since backtests usually take years, default to "2y" for interval "1d"
            history_data = await MarketDataService.get_history(symbol, interval="1d", period="2y")
            df = pd.DataFrame(history_data)
            if not df.empty and "time" in df.columns:
                # Try parsing as ISO format first, fallback to numeric/s if needed
                df["time"] = pd.to_datetime(df["time"], utc=True)
                df.set_index("time", inplace=True)
                df.sort_index(inplace=True)

            if df.empty or len(df) < 5:
                raise ValueError(f"Not enough historical data for {symbol}.")

            prices = df["close"].values
            dates = df.index.astype(str).values

            # 3. Fetch Real ML Signals from Database
            from app.models.instrument import Instrument
            from app.models.signal import EnsembleSignal

            sig_stmt = (
                select(EnsembleSignal)
                .where(
                    EnsembleSignal.symbol_id
                    == (select(Instrument.id).where(Instrument.symbol == symbol).scalar_subquery())
                )
                .order_by(EnsembleSignal.time.asc())
            )
            sig_res = await db.execute(sig_stmt)
            signal_records = sig_res.scalars().all()

            # Align signals with dates
            sig_dict = {}
            kelly_dict = {}
            for r in signal_records:
                d = r.time.date() if isinstance(r.time, datetime) else r.time
                sig_dict[str(d)] = float(r.signal)
                kelly_dict[str(d)] = (
                    float(r.kelly_fraction) if r.kelly_fraction is not None else 0.05
                )

            signals = np.zeros(len(dates))
            kellys = np.ones(len(dates)) * 0.05

            for i, d in enumerate(dates):
                # Ensure date string matches format used in dict
                d_str = str(d).split("T")[0]
                if d_str in sig_dict:
                    signals[i] = sig_dict[d_str]
                    kellys[i] = kelly_dict[d_str]
                else:
                    signals[i] = 0.0

            # 4. Run Event-Driven Engine
            def progress_cb(pct: int):
                asyncio.create_task(
                    ws_manager.broadcast(
                        "signals:backtest-progress",
                        {"job_id": job_id, "status": "RUNNING", "progress": pct},
                    )
                )

            backtester = EventDrivenBacktester(
                prices=prices,
                signals=signals,
                dates=dates,
                initial_capital=float(job.initial_capital),
                kelly_fraction=kellys,
                target_vol=0.15,
            )

            result = backtester.run(progress_callback=progress_cb)

            # 5. Compute Metrics
            dd, dd_dur = max_drawdown(result.equity_curve)
            win_rate, profit_factor, expectancy = trade_metrics(result.pnl)

            trades = result.pnl[result.pnl != 0]
            wins = trades[trades > 0]
            losses = trades[trades < 0]
            gross_profit = float(wins.sum()) if len(wins) else 0.0
            gross_loss = float(losses.sum()) if len(losses) else 0.0
            avg_win = float(wins.mean()) if len(wins) else 0.0
            avg_loss = float(losses.mean()) if len(losses) else 0.0
            payoff_ratio = float(abs(avg_win / avg_loss)) if avg_loss != 0 else 0.0

            total_return = (
                float(result.equity_curve[-1] / result.equity_curve[0] - 1.0)
                if len(result.equity_curve) >= 2 and result.equity_curve[0] != 0
                else 0.0
            )
            sharpe = float(sharpe_ratio(result.daily_returns))
            sortino = float(sortino_ratio(result.daily_returns))
            calmar = float(calmar_ratio(result.equity_curve))

            daily_returns = result.daily_returns
            positive_sum = float(daily_returns[daily_returns > 0].sum())
            negative_sum = float(-daily_returns[daily_returns < 0].sum())
            omega_ratio = positive_sum / negative_sum if negative_sum > 0 else 0.0
            tail_ratio = (
                float(abs(np.percentile(daily_returns, 95) / np.percentile(daily_returns, 5)))
                if len(daily_returns) > 0 and np.percentile(daily_returns, 5) != 0
                else 0.0
            )
            # Serenity ratio: CAGR / Ulcer Index (RMS of drawdowns, penalizes depth+duration of DDs)
            equity = result.equity_curve
            running_max = np.maximum.accumulate(equity)
            drawdown_series = np.where(running_max > 0, (equity - running_max) / running_max, 0.0)
            ulcer_index = (
                float(np.sqrt(np.mean(np.square(drawdown_series)))) if len(drawdown_series) else 0.0
            )
            serenity_ratio = (
                float(cagr(result.equity_curve) / ulcer_index) if ulcer_index > 0 else 0.0
            )
            # Deflated Sharpe: penalize the raw Sharpe by sample-size uncertainty (simplified — not a
            # full multiple-testing correction, just a real, computed confidence discount).
            n_obs = len(daily_returns)
            deflated_sharpe = (
                float(sharpe * np.sqrt(max(n_obs - 1, 1) / max(n_obs, 1))) if n_obs > 0 else 0.0
            )

            metrics = {
                "total_return": total_return,
                "cagr": float(cagr(result.equity_curve)),
                "sharpe": sharpe,
                "sharpe_ratio": sharpe,
                "sortino_ratio": sortino,
                "calmar_ratio": calmar,
                "omega_ratio": omega_ratio,
                "max_drawdown": float(dd),
                "max_drawdown_duration_days": int(dd_dur),
                "win_rate": float(win_rate),
                "profit_factor": float(profit_factor),
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "payoff_ratio": payoff_ratio,
                "num_trades": int(len(trades)),
                "gross_profit": gross_profit,
                "gross_loss": gross_loss,
                "tail_ratio": tail_ratio,
                "serenity_ratio": serenity_ratio,
                "deflated_sharpe": deflated_sharpe,
                "expectancy": float(expectancy),
                "turnover": float(
                    calculate_turnover(result.positions, prices, float(job.initial_capital))
                ),
            }

            # 6. Save Results — build response-schema-shaped structures (EquityCurvePoint,
            # DrawdownPoint, TradeLogEntry all expect per-date mapping objects, not bare arrays).
            date_strs = [str(d).split("T")[0] for d in dates]
            date_index = {d: i for i, d in enumerate(date_strs)}

            equity_curve_points = [
                {"date": d, "portfolio_value": float(v)}
                for d, v in zip(date_strs, result.equity_curve, strict=False)
            ]
            drawdown_series_points = [
                {"date": d, "drawdown_pct": float(dd_val * 100)}
                for d, dd_val in zip(date_strs, drawdown_series, strict=False)
            ]
            trade_log_entries = []
            for tr in result.trades_log:
                d_str = str(tr["date"]).split("T")[0]
                idx = date_index.get(d_str)
                pnl_val = float(result.pnl[idx]) if idx is not None else 0.0
                qty = float(tr["qty"])
                if qty == 0:
                    continue
                trade_log_entries.append(
                    {
                        "date": d_str,
                        "symbol": symbol,
                        "direction": tr["side"],
                        "quantity": abs(qty),
                        "price": float(tr["price"]),
                        "pnl": pnl_val,
                    }
                )

            job.results = {
                "metrics": metrics,
                "equity_curve": equity_curve_points,
                "drawdown_series": drawdown_series_points,
                "trade_log": trade_log_entries,
                "daily_returns": result.daily_returns.tolist(),
                "dates": date_strs,
            }
            job.status = "DONE"
            job.completed_at = datetime.now(UTC)

            await db.commit()
            await ws_manager.broadcast(
                "signals:backtest-progress",
                {"job_id": job_id, "status": "DONE", "progress": 100, "metrics": metrics},
            )

            logger.info(f"BacktestJob {job_id} completed successfully.")

        except Exception as e:
            logger.exception(f"BacktestJob {job_id} failed: {e}")
            job.status = "FAILED"
            job.results = {"error": str(e)}
            job.completed_at = datetime.now(UTC)
            await db.commit()
            await ws_manager.broadcast(
                "signals:backtest-progress",
                {"job_id": job_id, "status": "FAILED", "progress": 100, "error": str(e)},
            )


@shared_task(name="run_backtest_job_task")
def run_backtest_job_task(job_id: str) -> None:
    """Celery task entry point to run backtest.

    In a real worker process there's no event loop running, so asyncio.run() works
    directly. In dev (task_always_eager=True) this executes inline inside the FastAPI
    request's own event loop, where asyncio.run() would raise — run it on a separate
    thread with its own loop in that case instead.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(run_backtest_async(job_id))
        return

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(asyncio.run, run_backtest_async(job_id)).result()
