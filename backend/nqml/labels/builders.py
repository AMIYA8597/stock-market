"""
Label functions for NQML.
"""

import numpy as np
import pandas as pd

from nqml.labels.registry import label


@label("dir_1d")
def dir_1d(bars: pd.DataFrame) -> pd.Series:
    """Direction of 1-day forward return."""
    ret = bars["adj_close"].pct_change(1).shift(-1)
    return np.sign(ret).fillna(0).astype("int8")


@label("dir_1d_dz")
def dir_1d_dz(bars: pd.DataFrame) -> pd.Series:
    """Direction of 1-day forward return with 10bps deadzone."""
    ret = bars["adj_close"].pct_change(1).shift(-1)
    out = pd.Series(0, index=bars.index, dtype="int8")
    out[ret > 0.0010] = 1
    out[ret < -0.0010] = -1
    out[ret.isna()] = 0
    return out


@label("dir_5d")
def dir_5d(bars: pd.DataFrame) -> pd.Series:
    """Direction of 5-day forward return."""
    ret = bars["adj_close"].pct_change(5).shift(-5)
    return np.sign(ret).fillna(0).astype("int8")


@label("triple_barrier")
def triple_barrier(bars: pd.DataFrame) -> pd.Series:
    """
    Simplified vector triple barrier.
    pt=1%, sl=1%, window=5.
    Returns 1 if PT hit first, -1 if SL hit first, 0 if time expiry.
    """
    close = bars["adj_close"].values
    n = len(close)
    out = np.zeros(n, dtype=np.int8)

    # We do a fast rolling lookahead
    for i in range(n):
        c0 = close[i]
        if c0 == 0 or np.isnan(c0):
            continue
        pt = c0 * 1.01
        sl = c0 * 0.99
        hit = 0
        for j in range(i + 1, min(i + 6, n)):
            c1 = close[j]
            if c1 >= pt:
                hit = 1
                break
            elif c1 <= sl:
                hit = -1
                break
        out[i] = hit

    return pd.Series(out, index=bars.index, dtype="int8")
