"""Evaluation metrics for TFT quantile forecasting."""

from __future__ import annotations

import numpy as np
from scipy import stats


def quantile_loss(y_true: np.ndarray, y_pred_q: np.ndarray, quantiles: tuple[float, ...] = (0.1, 0.5, 0.9)) -> float:
    r"""
    Compute pinball (quantile) loss.

    The pinball loss for quantile q is:
    QL_q = Σ_t [q·max(y_t - ŷ_{q,t}, 0) + (1-q)·max(ŷ_{q,t} - y_t, 0)]

    This penalizes overestimation by (1-q) and underestimation by q, controlling
    the calibration of prediction intervals.

    Args:
        y_true: Observed values of shape (N,) or (N, 1) or (N, horizon).
        y_pred_q: Quantile predictions of shape (N, n_quantiles) or (N, horizon, n_quantiles).
        quantiles: Tuple of quantile levels, default (0.1, 0.5, 0.9) for deciles.

    Returns:
        Scalar average pinball loss across all quantiles and samples.

    Example:
        >>> y_true = np.array([1.0, 2.0, 3.0])
        >>> y_pred = np.array([[0.9, 1.0, 1.1],
        ...                    [1.9, 2.0, 2.1],
        ...                    [2.9, 3.0, 3.1]])
        >>> loss = quantile_loss(y_true, y_pred, quantiles=(0.1, 0.5, 0.9))
    """
    y = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred_q, dtype=float)

    if yp.ndim == 2:
        if yp.shape[-1] != len(quantiles):
            raise ValueError(f"Last dimension of y_pred_q ({yp.shape[-1]}) must match number of quantiles ({len(quantiles)})")
    else:
        raise ValueError(f"y_pred_q must be 2D, got shape {yp.shape}")

    total = 0.0
    for i, q in enumerate(quantiles):
        err = y.ravel() - yp[:, i]
        total += np.mean(np.maximum(q * err, (q - 1.0) * err))

    return float(total / len(quantiles))


def p50_rmse(y_true: np.ndarray, y_pred_median: np.ndarray) -> float:
    r"""
    Root mean squared error on median (P50) forecast.

    RMSE = √(Σ_t (y_t - ŷ_{0.5,t})² / N)

    Args:
        y_true: Observed values of shape (N,).
        y_pred_median: Median predictions of shape (N,).

    Returns:
        RMSE value.
    """
    y = np.asarray(y_true, dtype=float).ravel()
    yp = np.asarray(y_pred_median, dtype=float).ravel()
    return float(np.sqrt(np.mean((y - yp) ** 2)))


def winkler_score_coverage(
    y_true: np.ndarray,
    p10: np.ndarray,
    p90: np.ndarray,
    alpha: float = 0.2,
) -> tuple[float, float]:
    r"""
    Compute Winkler score and empirical coverage of prediction interval [P10, P90].

    Winkler Score penalizes both interval width and miscoverage:
    W = (P90 - P10) + (2/α)·max(P10 - y, 0) + (2/α)·max(y - P90, 0)

    Lower is better. Coverage should approach (1 - α) = 0.8 for α=0.2.

    Args:
        y_true: Observed values shape (N,).
        p10: Lower bound (10th percentile) shape (N,).
        p90: Upper bound (90th percentile) shape (N,).
        alpha: Confidence level parameter (default 0.2 for 80% interval).

    Returns:
        (winkler_score, coverage) tuple where coverage ∈ [0, 1].

    Example:
        >>> y_obs = np.array([1.0, 2.0, 3.0])
        >>> pred_lo = np.array([0.8, 1.8, 2.8])
        >>> pred_hi = np.array([1.2, 2.2, 3.2])
        >>> ws, cov = winkler_score_coverage(y_obs, pred_lo, pred_hi)
        >>> print(f"Winkler: {ws:.3f}, Coverage: {cov:.1%}")
    """
    y = np.asarray(y_true, dtype=float).ravel()
    lo = np.asarray(p10, dtype=float).ravel()
    hi = np.asarray(p90, dtype=float).ravel()

    if not (len(y) == len(lo) == len(hi)):
        raise ValueError("All inputs must have same length")

    width = hi - lo
    below = y < lo
    above = y > hi

    penalty = np.where(below, (2.0 / alpha) * (lo - y), 0.0) + np.where(above, (2.0 / alpha) * (y - hi), 0.0)
    winkler = float(np.mean(width + penalty))
    coverage = float(np.mean((y >= lo) & (y <= hi)))

    return winkler, coverage


def diebold_mariano_test(
    pred_tft: np.ndarray,
    pred_baseline: np.ndarray,
    y_true: np.ndarray,
) -> tuple[float, float]:
    r"""
    Diebold-Mariano test for forecast comparison.

    Tests H0: TFT and baseline have equal forecast accuracy.
    Computes loss differential: d_t = |y_t - ŷ_TFT,t|² - |y_t - ŷ_baseline,t|²
    DM statistic = Ē(d) / √(Var(d) / N) ~ N(0,1) under H0.

    Args:
        pred_tft: TFT median predictions shape (N,).
        pred_baseline: Baseline (e.g., ARIMA) predictions shape (N,).
        y_true: Observed values shape (N,).

    Returns:
        (dm_statistic, p_value) tuple where p_value is two-tailed.
        If p_value < 0.05, TFT significantly outperforms baseline.

    Example:
        >>> y = np.array([1.0, 2.0, 3.0, 4.0])
        >>> pred_tft = np.array([1.1, 2.0, 3.1, 3.9])
        >>> pred_ar = np.array([0.9, 2.2, 2.9, 4.1])
        >>> stat, pval = diebold_mariano_test(pred_tft, pred_ar, y)
        >>> print(f"DM stat: {stat:.3f}, p-value: {pval:.3f}")
    """
    y = np.asarray(y_true, dtype=float).ravel()
    pred_t = np.asarray(pred_tft, dtype=float).ravel()
    pred_b = np.asarray(pred_baseline, dtype=float).ravel()

    if not (len(y) == len(pred_t) == len(pred_b)):
        raise ValueError("All inputs must have same length")

    loss_diff = (y - pred_t) ** 2 - (y - pred_b) ** 2
    mean_diff = np.mean(loss_diff)
    var_diff = np.var(loss_diff, ddof=1)
    n = len(loss_diff)

    if var_diff < 1e-12:
        # Predictions are identical
        return 0.0, 1.0

    dm_stat = mean_diff / np.sqrt(var_diff / n)
    p_value = 2.0 * (1.0 - stats.norm.cdf(abs(dm_stat)))

    return float(dm_stat), float(p_value)


def compute_metrics_summary(
    y_true: np.ndarray,
    y_pred_q: np.ndarray,
    quantiles: tuple[float, ...] = (0.1, 0.5, 0.9),
) -> dict[str, float]:
    r"""
    Comprehensive evaluation metrics for quantile forecasting.

    Computes all key metrics in one pass:
    - Quantile loss (pinball loss)
    - RMSE on median
    - Winkler score coverage
    - Interval width statistics

    Args:
        y_true: Observed values shape (N,).
        y_pred_q: Quantile predictions shape (N, n_quantiles).
        quantiles: Quantile levels, default (0.1, 0.5, 0.9).

    Returns:
        Dictionary with keys:
        - 'quantile_loss': Pinball loss
        - 'p50_rmse': RMSE on P50
        - 'winkler_score': Winkler score
        - 'coverage': Empirical coverage of [P10, P90]
        - 'interval_width_mean': Mean width of [P10, P90]
        - 'interval_width_std': Std dev of interval widths

    Example:
        >>> metrics = compute_metrics_summary(y_true, y_pred_q)
        >>> print(f"Quantile loss: {metrics['quantile_loss']:.4f}")
        >>> print(f"Coverage: {metrics['coverage']:.1%}")
    """
    y_pred_q = np.asarray(y_pred_q, dtype=float)
    y_true = np.asarray(y_true, dtype=float).ravel()

    idx_p10 = 0
    idx_p50 = 1
    idx_p90 = 2

    ql = quantile_loss(y_true, y_pred_q, quantiles)
    rmse = p50_rmse(y_true, y_pred_q[:, idx_p50])
    ws, cov = winkler_score_coverage(y_true, y_pred_q[:, idx_p10], y_pred_q[:, idx_p90])

    widths = y_pred_q[:, idx_p90] - y_pred_q[:, idx_p10]

    return {
        "quantile_loss": float(ql),
        "p50_rmse": float(rmse),
        "winkler_score": float(ws),
        "coverage": float(cov),
        "interval_width_mean": float(np.mean(widths)),
        "interval_width_std": float(np.std(widths)),
    }

