# research/backtesting stub

import numpy as np


class BacktestResult:
    def __init__(self, T, N):
        self.positions = np.zeros((T, N))
        self.equity_curve = np.linspace(100000, 100000 * (1 + 0.0002 * T), T)
        self.daily_returns = np.diff(self.equity_curve) / self.equity_curve[:-1]

def run_vectorized_backtest(signals, prices, kelly_fraction, initial_capital):
    """Simple placeholder returning dummy backtest results.
    signals, prices, kelly_fraction are expected numpy arrays.
    """
    T, N = signals.shape
    return BacktestResult(T, N)
