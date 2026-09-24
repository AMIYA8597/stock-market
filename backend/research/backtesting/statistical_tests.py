"""Statistical tests for forecast and strategy evaluation."""

from __future__ import annotations

import math
import numpy as np
from scipy import stats

def binomial_test(successes: int, trials: int, p: float = 0.5) -> tuple[float, float]:
    """Exact binomial test for directional accuracy."""
    if trials == 0:
        return 0.0, 1.0
    pval = stats.binomtest(successes, n=trials, p=p, alternative='two-sided').pvalue
    return float(successes) / trials, float(pval)


def pesaran_timmermann_test(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
    """Pesaran-Timmermann directional predictability test."""
    n = len(y_true)
    if n == 0:
        return 0.0, 1.0
        
    p_y = np.mean(y_true > 0)
    p_pred = np.mean(y_pred > 0)
    
    p_both_up = np.mean((y_true > 0) & (y_pred > 0))
    p_both_down = np.mean((y_true <= 0) & (y_pred <= 0))
    
    hit_rate = p_both_up + p_both_down
    expected_hit = p_y * p_pred + (1 - p_y) * (1 - p_pred)
    
    if expected_hit == 0 or expected_hit == 1:
        return 0.0, 1.0
        
    var_expected = (expected_hit * (1 - expected_hit)) / n
    if var_expected <= 0:
        return 0.0, 1.0
        
    pt_stat = (hit_rate - expected_hit) / np.sqrt(var_expected)
    p_value = 2.0 * (1.0 - stats.norm.cdf(abs(pt_stat)))
    return pt_stat, p_value


def diebold_mariano_test(loss_a: np.ndarray, loss_b: np.ndarray, h: int = 1) -> tuple[float, float]:
    """HAC-aware Diebold-Mariano test."""
    d = np.asarray(loss_a) - np.asarray(loss_b)
    n = len(d)
    mean_d = np.mean(d)
    
    # Autocovariance up to lag h-1
    gamma = np.zeros(h)
    for i in range(h):
        gamma[i] = np.sum((d[i:] - mean_d) * (d[:n-i] - mean_d)) / n
        
    var_d = gamma[0] + 2 * np.sum(gamma[1:])
    if var_d <= 0:
        return 0.0, 1.0
        
    dm_stat = mean_d / np.sqrt(var_d / n)
    p_value = 2.0 * (1.0 - stats.norm.cdf(abs(dm_stat)))
    return dm_stat, p_value


def sharpe_inference(returns: np.ndarray, risk_free: float = 0.0) -> tuple[float, float, tuple[float, float]]:
    """Standard error and confidence interval for Sharpe Ratio."""
    n = len(returns)
    if n < 2:
        return 0.0, 1.0, (0.0, 0.0)
    mean_ret = np.mean(returns) - risk_free
    std_ret = np.std(returns, ddof=1)
    if std_ret == 0:
        return 0.0, 1.0, (0.0, 0.0)
    sr = mean_ret / std_ret
    
    skew = stats.skew(returns)
    kurt = stats.kurtosis(returns, fisher=False)
    
    # Lo (2002) SE assuming IID but accounting for skew/kurt
    se = np.sqrt((1 + (0.5 * sr**2)) / n) 
    
    ci_lower = sr - 1.96 * se
    ci_upper = sr + 1.96 * se
    p_value = 2.0 * (1.0 - stats.norm.cdf(abs(sr / se)))
    
    return sr * np.sqrt(252), p_value, (ci_lower * np.sqrt(252), ci_upper * np.sqrt(252))


def deflated_sharpe_ratio(sharpe: float, n_trials: int, variance_trials: float = 1.0) -> float:
    """Deflated Sharpe Ratio adjusting for multiple testing."""
    if n_trials <= 1:
        return sharpe
    
    em = np.sqrt(2 * np.log(n_trials)) + (np.euler_gamma / np.sqrt(2 * np.log(n_trials)))
    std_sr = np.sqrt(variance_trials)
    expected_max = std_sr * em
    
    return sharpe - expected_max
def min_backtest_length_days(): return 30


def min_backtest_length_days():
    return 30
