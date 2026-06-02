"""Base contracts for feature engineering builders."""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class FeatureBuilder(ABC):
    """Abstract feature builder interface.

    All builders must be causality-safe: features at time t may only use data up to t.
    """

    name: str

    def fit(self, frame: pd.DataFrame) -> FeatureBuilder:
        """Optional fit hook for builders that require calibration."""
        del frame
        return self

    @abstractmethod
    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Transform input market frame into derived feature columns."""

    def fit_transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform in one call."""
        return self.fit(frame).transform(frame)
