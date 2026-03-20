"""Rolling Fama-French style beta factor estimation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from research.feature_engineering.base import FeatureBuilder


class FF5BetasBuilder(FeatureBuilder):
    """Estimate rolling linear betas to five factor returns.

    Expected factor columns: mkt_rf, smb, hml, rmw, cma.
    """

    name = "ff5_betas"

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        data = frame.sort_values("time").copy()
        if "ret_1d" not in data.columns:
            return data

        factors = ["mkt_rf", "smb", "hml", "rmw", "cma"]
        for factor in factors:
            if factor not in data.columns:
                data[factor] = 0.0

        y = data["ret_1d"].astype(float).to_numpy()
        x = data[factors].astype(float).to_numpy()
        window = 126

        betas = np.full((len(data), 5), np.nan)
        for i in range(window - 1, len(data)):
            y_w = y[i - window + 1 : i + 1]
            x_w = x[i - window + 1 : i + 1]
            x_design = np.column_stack([np.ones(len(x_w)), x_w])
            coef, *_ = np.linalg.lstsq(x_design, y_w, rcond=None)
            betas[i, :] = coef[1:]

        for j, factor in enumerate(factors):
            data[f"beta_{factor}"] = betas[:, j]

        return data
