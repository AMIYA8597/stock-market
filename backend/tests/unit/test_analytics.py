import numpy as np

from research.backtesting.analytics import cagr, max_drawdown, sharpe_ratio, trade_metrics


def test_analytics_metrics():
    # Synthetic equity curve from 100k to 120k over 252 days (1 year)
    equity = np.linspace(100000, 120000, 252)
    # Add a dip for drawdown
    equity[100:150] -= 5000

    returns = np.diff(equity) / equity[:-1]

    c = cagr(equity)
    assert 0.19 < c < 0.21  # ~20% return

    dd, dur = max_drawdown(equity)
    assert dd < 0
    assert dur > 0

    s = sharpe_ratio(returns, rf_daily=0.0)
    assert s > 0

    # Trade metrics
    pnl = np.array([100.0, -50.0, 200.0, -10.0])
    wr, pf, exp = trade_metrics(pnl)
    assert wr == 0.5  # 2 wins, 2 losses
    assert pf == 300.0 / 60.0  # 5.0
    assert exp == (300.0 - 60.0) / 4.0  # 240 / 4 = 60.0

    # (Turnover test removed as it requires full price matrix and capital)
