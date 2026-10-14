import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import numpy as np
import pandas as pd
import pytest

from app.tasks.backtest_tasks import run_backtest_async, run_backtest_job_task


@pytest.fixture
def mock_job():
    job = MagicMock()
    job.id = uuid4()
    job.status = "PENDING"
    job.universe = ["AAPL"]
    job.initial_capital = 100000.0
    return job


@pytest.fixture
def mock_db_session():
    mock_session = AsyncMock()
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_session
    mock_db.__aexit__.return_value = False
    return mock_db, mock_session


@pytest.fixture
def mock_ws_manager():
    with patch(
        "app.tasks.backtest_tasks.ws_manager.broadcast", new_callable=AsyncMock
    ) as mock_broadcast:
        yield mock_broadcast


def make_bar(ts, price=100.0):
    bar = MagicMock()
    bar.timestamp = ts
    bar.open = price
    bar.high = price + 1
    bar.low = price - 1
    bar.close = price
    bar.volume = 1000
    return bar


@pytest.fixture
def mock_instrument_result():
    """MagicMock standing in for the `select(Instrument)...` query result."""
    res = MagicMock()
    inst = MagicMock()
    inst.id = uuid4()
    res.scalars.return_value.first.return_value = inst
    return res


@pytest.fixture
def mock_ohlcv_result_5_bars():
    """MagicMock standing in for the `select(OHLCV)...` query result, with
    enough bars (>= 5) to pass run_backtest_async's minimum-history check."""
    res = MagicMock()
    dates = pd.date_range(start="2022-01-01", periods=5, tz="UTC")
    res.scalars.return_value.all.return_value = [make_bar(d) for d in dates]
    return res


@pytest.fixture
def mock_ohlcv_result_empty():
    """MagicMock for a `select(OHLCV)...` query result with no bars, to
    exercise the 'not enough historical data' failure path."""
    res = MagicMock()
    res.scalars.return_value.all.return_value = []
    return res


@pytest.mark.asyncio
@patch("app.tasks.backtest_tasks.async_session_factory")
async def test_run_backtest_async_job_not_found(
    mock_session_factory, mock_db_session, mock_ws_manager
):
    mock_db, mock_session = mock_db_session
    mock_session_factory.return_value = mock_db

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_res

    job_id = str(uuid4())
    await run_backtest_async(job_id)

    mock_session.execute.assert_called_once()
    mock_ws_manager.assert_not_called()


@pytest.mark.asyncio
@patch("app.tasks.backtest_tasks.async_session_factory")
async def test_run_backtest_async_not_enough_data(
    mock_session_factory,
    mock_db_session,
    mock_ws_manager,
    mock_job,
    mock_instrument_result,
    mock_ohlcv_result_empty,
):
    mock_db, mock_session = mock_db_session
    mock_session_factory.return_value = mock_db

    mock_res_job = MagicMock()
    mock_res_job.scalar_one_or_none.return_value = mock_job

    # run_backtest_async issues, in order: select(BacktestJob), then
    # select(Instrument), then select(OHLCV) - which here returns no bars,
    # triggering the "Not enough historical data" failure before any signal
    # query is reached.
    mock_session.execute = AsyncMock(
        side_effect=[mock_res_job, mock_instrument_result, mock_ohlcv_result_empty]
    )

    job_id = str(mock_job.id)
    await run_backtest_async(job_id)

    assert mock_job.status == "FAILED"
    mock_ws_manager.assert_called_with(
        "signals:backtest-progress",
        {
            "job_id": job_id,
            "status": "FAILED",
            "progress": 100,
            "error": "Not enough historical data for AAPL.",
        },
    )


@pytest.mark.asyncio
@patch("app.tasks.backtest_tasks.async_session_factory")
async def test_run_backtest_async_success(
    mock_session_factory,
    mock_db_session,
    mock_ws_manager,
    mock_job,
    mock_instrument_result,
    mock_ohlcv_result_5_bars,
):
    mock_db, mock_session = mock_db_session
    mock_session_factory.return_value = mock_db

    mock_res_job = MagicMock()
    mock_res_job.scalar_one_or_none.return_value = mock_job

    mock_res_sig = MagicMock()
    mock_signal = MagicMock()
    mock_signal.time = "2022-01-02 00:00:00+00:00"
    mock_signal.signal = 1.0
    mock_signal.kelly_fraction = 0.1

    mock_signal2 = MagicMock()
    mock_signal2.time = "2022-01-03 00:00:00+00:00"
    mock_signal2.signal = -1.0
    mock_signal2.kelly_fraction = None
    mock_res_sig.scalars.return_value.all.return_value = [mock_signal, mock_signal2]

    # run_backtest_async issues 4 queries in order: BacktestJob, Instrument,
    # OHLCV (5 bars, passes the minimum-history check), then EnsembleSignal.
    mock_session.execute = AsyncMock(
        side_effect=[mock_res_job, mock_instrument_result, mock_ohlcv_result_5_bars, mock_res_sig]
    )

    with patch("app.tasks.backtest_tasks.EventDrivenBacktester") as MockBacktester:
        mock_backtester_inst = MockBacktester.return_value

        mock_result = MagicMock()
        mock_result.equity_curve = np.array([100000, 101000, 102000, 99000, 105000])
        mock_result.pnl = np.array([0, 1000, 1000, -3000, 6000])
        mock_result.daily_returns = np.array([0.0, 0.01, 0.01, -0.03, 0.06])
        mock_result.positions = np.array([0, 10, 10, -10, 20])
        mock_result.trades_log = [
            {"date": "2022-01-02", "side": "BUY", "qty": 10, "price": 100.0},
            {"date": "2022-01-03", "side": "SELL", "qty": -20, "price": 101.0},
            {"date": "2022-01-04", "side": "BUY", "qty": 0, "price": 100.0},
        ]

        mock_backtester_inst.run.return_value = mock_result

        job_id = str(mock_job.id)
        await run_backtest_async(job_id)

        assert mock_job.status == "DONE"
        assert "metrics" in mock_job.results
        assert "trade_log" in mock_job.results

        mock_ws_manager.assert_called_with(
            "signals:backtest-progress",
            {
                "job_id": job_id,
                "status": "DONE",
                "progress": 100,
                "metrics": mock_job.results["metrics"],
            },
        )

        progress_cb = mock_backtester_inst.run.call_args[1]["progress_callback"]
        progress_cb(50)
        await asyncio.sleep(0)
        mock_ws_manager.assert_any_call(
            "signals:backtest-progress", {"job_id": job_id, "status": "RUNNING", "progress": 50}
        )


@patch("app.tasks.backtest_tasks.asyncio.get_running_loop")
@patch("app.tasks.backtest_tasks.asyncio.run")
def test_run_backtest_job_task_no_loop(mock_run, mock_get_loop):
    mock_get_loop.side_effect = RuntimeError("no running event loop")

    run_backtest_job_task("job-id")
    mock_run.assert_called_once()
    assert mock_run.call_args[0][0].__name__ == "run_backtest_async"


@patch("app.tasks.backtest_tasks.asyncio.get_running_loop")
@patch("concurrent.futures.ThreadPoolExecutor")
def test_run_backtest_job_task_with_loop(mock_executor, mock_get_loop):
    mock_get_loop.return_value = MagicMock()
    mock_pool = MagicMock()
    mock_executor.return_value.__enter__.return_value = mock_pool
    mock_future = MagicMock()
    mock_pool.submit.return_value = mock_future

    run_backtest_job_task("job-id")
    mock_pool.submit.assert_called_once()
