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
                "signals:backtest-progress",
                {"job_id": job_id, "status": "RUNNING", "progress": 0}
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
            from app.models.signal import EnsembleSignal
            from app.models.instrument import Instrument

            sig_stmt = select(EnsembleSignal).where(
                EnsembleSignal.symbol_id == (
                    select(Instrument.id)
                    .where(Instrument.symbol == symbol)
                    .scalar_subquery()
                )
            ).order_by(EnsembleSignal.time.asc())
            sig_res = await db.execute(sig_stmt)
            signal_records = sig_res.scalars().all()

            # Align signals with dates
            sig_dict = {}
            kelly_dict = {}
            for r in signal_records:
                d = r.time.date() if isinstance(r.time, datetime) else r.time
                sig_dict[str(d)] = float(r.signal)
                kelly_dict[str(d)] = float(r.kelly_fraction) if r.kelly_fraction is not None else 0.05

            signals = np.zeros(len(dates))
            kellys = np.ones(len(dates)) * 0.05

            for i, d in enumerate(dates):
                # Ensure date string matches format used in dict
                d_str = str(d).split('T')[0]
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
                        {"job_id": job_id, "status": "RUNNING", "progress": pct}
                    )
                )

            backtester = EventDrivenBacktester(
                prices=prices,
                signals=signals,
                dates=dates,
                initial_capital=float(job.initial_capital),
                kelly_fraction=kellys,
                target_vol=0.15
            )

            result = backtester.run(progress_callback=progress_cb)

            # 5. Compute Metrics
            dd, dd_dur = max_drawdown(result.equity_curve)
            win_rate, profit_factor, expectancy = trade_metrics(result.pnl)

            metrics = {
                "cagr": float(cagr(result.equity_curve)),
                "sharpe": float(sharpe_ratio(result.daily_returns)),
                "sortino": float(sortino_ratio(result.daily_returns)),
                "calmar": float(calmar_ratio(result.equity_curve)),
                "max_drawdown": float(dd),
                "drawdown_duration": int(dd_dur),
                "win_rate": float(win_rate),
                "profit_factor": float(profit_factor),
                "expectancy": float(expectancy),
                "turnover": float(calculate_turnover(result.positions, prices, float(job.initial_capital)))
            }

            # 6. Save Results
            job.results = {
                "metrics": metrics,
                "equity_curve": result.equity_curve.tolist(),
                "daily_returns": result.daily_returns.tolist(),
                "trades_log": result.trades_log,
                "dates": dates.tolist()
            }
            job.status = "DONE"
            job.completed_at = datetime.now(UTC)

            await db.commit()
            await ws_manager.broadcast(
                "signals:backtest-progress",
                {"job_id": job_id, "status": "DONE", "progress": 100, "metrics": metrics}
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
                {"job_id": job_id, "status": "FAILED", "progress": 100, "error": str(e)}
            )


@shared_task(name="run_backtest_job_task")
def run_backtest_job_task(job_id: str) -> None:
    """Celery task entry point to run backtest."""
    asyncio.run(run_backtest_async(job_id))
