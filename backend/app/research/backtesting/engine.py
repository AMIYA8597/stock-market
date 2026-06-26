# research/backtesting stub

import numpy as np

class BacktestResult:
    def __init__(self, T, N):
        self.positions = np.zeros((T, N))
        self.equity_curve = np.cumprod(1 + np.random.normal(0.0002, 0.01, size=T)) * 100000
        self.daily_returns = np.diff(self.equity_curve) / self.equity_curve[:-1]

def run_vectorized_backtest(signals, prices, kelly_fraction, initial_capital):
    """Simple placeholder returning dummy backtest results.
    signals, prices, kelly_fraction are expected numpy arrays.
    """
    T, N = signals.shape
    return BacktestResult(T, N)
