"""Hierarchical Risk Parity implementation."""

from __future__ import annotations

import numpy as np
from scipy.cluster.hierarchy import linkage


def _corr_distance(corr: np.ndarray) -> np.ndarray:
    return np.sqrt((1.0 - corr) / 2.0)


def _cluster_variance(cov: np.ndarray, idx: np.ndarray) -> float:
    sub = cov[np.ix_(idx, idx)]
    ivp = 1.0 / np.diag(sub)
    ivp = ivp / ivp.sum()
    return float(ivp.T @ sub @ ivp)


def _recursive_bisection(cov: np.ndarray, sort_ix: np.ndarray) -> np.ndarray:
    w = np.ones(len(sort_ix))
    clusters = [sort_ix]

    while clusters:
        cluster = clusters.pop(0)
        if len(cluster) <= 1:
            continue

        split = len(cluster) // 2
        left = cluster[:split]
        right = cluster[split:]

        v_left = _cluster_variance(cov, left)
        v_right = _cluster_variance(cov, right)
        alpha = v_right / max(v_left + v_right, 1e-12)

        left_mask = np.isin(sort_ix, left)
        right_mask = np.isin(sort_ix, right)
        w[left_mask] *= alpha
        w[right_mask] *= 1.0 - alpha

        clusters.append(left)
        clusters.append(right)

    w = w / w.sum()
    return w


def hrp_weights(returns: np.ndarray) -> np.ndarray:
    """Compute HRP weights using Ward linkage and recursive bisection."""
    r = np.asarray(returns, dtype=float)
    cov = np.cov(r, rowvar=False)
    corr = np.corrcoef(r, rowvar=False)
    dist = _corr_distance(corr)

    tri = dist[np.triu_indices(dist.shape[0], k=1)]
    z = linkage(tri, method="ward")
    sort_ix = np.array(list(map(int, z[:, :2].flatten())))
    sort_ix = np.unique(sort_ix[sort_ix < cov.shape[0]])

    if len(sort_ix) < cov.shape[0]:
        missing = np.setdiff1d(np.arange(cov.shape[0]), sort_ix)
        sort_ix = np.concatenate([sort_ix, missing])

    w_sorted = _recursive_bisection(cov, sort_ix)
    w = np.zeros(cov.shape[0])
    for i, idx in enumerate(sort_ix):
        w[idx] = w_sorted[i]
    return w / w.sum()
