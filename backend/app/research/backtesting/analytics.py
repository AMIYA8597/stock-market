# research/backtesting/analytics stub

def sharpe_ratio(returns):
    """Return a dummy Sharpe ratio (mean/std)."""
    import numpy as np
    returns = np.array(returns)
    if returns.size == 0:
        return 0.0
    mean = returns.mean()
    std = returns.std() if returns.std() != 0 else 1e-9
    return mean / std

def sortino_ratio(returns):
    """Return dummy Sortino ratio (mean/downside std)."""
    import numpy as np
    returns = np.array(returns)
    mean = returns.mean()
    downside = returns[returns < 0]
    std_down = downside.std() if downside.size > 0 else 1e-9
    return mean / std_down

def max_drawdown(equity_curve):
    """Return (max_dd, duration_days) dummy values."""
    import numpy as np
    equity = np.array(equity_curve)
    if equity.size == 0:
        return 0.0, 0
    roll_max = np.maximum.accumulate(equity)
    drawdowns = (equity - roll_max) / roll_max
    max_dd = drawdowns.min()
    # dummy duration as index diff
    duration = int(np.argmax(drawdowns == max_dd))
    return max_dd, duration

def cagr(equity_curve):
    """Compound annual growth rate placeholder."""
    import numpy as np
    equity = np.array(equity_curve)
    if equity.size < 2:
        return 0.0
    total_return = equity[-1] / equity[0] - 1
    years = len(equity) / 252  # assume 252 trading days per year
    return (1 + total_return) ** (1 / years) - 1

def calmar_ratio(equity_curve):
    """Return dummy Calmar ratio (CAGR / max DD)."""
    c = cagr(equity_curve)
    md, _ = max_drawdown(equity_curve)
    return c / (-md) if md != 0 else 0.0

def omega_ratio(returns):
    """Return dummy Omega ratio (gain/loss)."""
    import numpy as np
    returns = np.array(returns)
    gain = returns[returns > 0].sum()
    loss = -returns[returns < 0].sum()
    return gain / loss if loss != 0 else float('inf')
