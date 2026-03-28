"""Inference engine for HMM-GARCH regime detection and volatility forecasting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from research.models.hmm_garch.regime_detector import RegimeDetectionResult, detect_regime
from research.models.hmm_garch.hmm import StudentTHMM


@dataclass(slots=True)
class HMMGARCHInference:
    """
    Inference output for regime detection and volatility forecasting.

    Attributes:
        current_state: Integer state index ∈ [0, 3]
            0=BULL, 1=BEAR, 2=SIDEWAYS, 3=CRISIS
        state_probs: 1D array of shape (4,) with state probabilities γ_t(k)
        conditional_vol: Current estimated conditional volatility σ_t
        vol_forecast_5d: 1D array of shape (5,) with 5-day ahead vol [σ_{t+1}, ..., σ_{t+5}]
        vol_forecast_21d: 1D array of shape (21,) with 21-day ahead vol [σ_{t+1}, ..., σ_{t+21}]
        hmm_model: Trained StudentTHMM instance for reproducibility
        detection_result: Full RegimeDetectionResult from detect_regime()
    """

    current_state: int
    state_probs: np.ndarray
    conditional_vol: float
    vol_forecast_5d: np.ndarray
    vol_forecast_21d: np.ndarray
    hmm_model: StudentTHMM
    detection_result: RegimeDetectionResult


class InferenceEngine:
    """
    Production inference engine for HMM-GARCH regime detection.

    Handles single-asset and batch-mode predictions, with proper handling of
    missing data, edge cases, and GPU readiness (though computation is CPU).
    """

    def __init__(self, hmm_model: StudentTHMM | None = None) -> None:
        """Initialize inference engine with optional pre-trained HMM.

        Args:
            hmm_model: Pre-trained HiddenMarkovModel. If None, creates fresh 4-state model.
        """
        self.hmm_model = hmm_model or StudentTHMM(n_states=4, max_iter=500, tol=1e-6)
        self._current_inference: HMMGARCHInference | None = None

    def predict(
        self,
        ohlcv_data: np.ndarray,
        train: bool = False,
    ) -> HMMGARCHInference:
        r"""
        Predict regime and volatility forecast for a market snapshot.

        **Mathematical Details:**

        Given return series {r_1, ..., r_T}:
        1. Fit HMM: maximize log p(r_1:T | θ) via Baum-Welch EM with Student-t emissions
        2. Compute backward probabilities β_t(k) = Σ_j A_{kj} p(r_{t+1}|j) β_{t+1}(j)
        3. State posteriors: γ_t(k) = (α̂_t(k) · β_t(k)) / Σ_j (α̂_t(j) · β_t(j))
        4. Conditional volatility: σ_t from GARCH(1,1) fitted per regime epoch
        5. N-step vol forecast via σ²_{t+h} = ω + α·ε²_{t+h-1} + β·σ²_{t+h-1}

        Args:
            ohlcv_data: Array of shape (T, 5) with OHLCV data [open, high, low, close, volume].
                Must have T ≥ 60 observations for reliable regime detection.
            train: If True, re-fit the HMM on provided data. If False, use pre-fitted model.

        Returns:
            HMMGARCHInference with current regime, state probabilities, and 5d/21d vol forecasts.

        Raises:
            ValueError: If ohlcv_data shape invalid or insufficient samples.
            RuntimeError: If HMM fitting fails to converge.

        Example:
            >>> import numpy as np
            >>> engine = InferenceEngine()
            >>> ohlcv = np.random.randn(252, 5)  # 1 year of daily OHLCV
            >>> result = engine.predict(ohlcv, train=True)
            >>> print(f"Regime: {result.current_state}, P(Bull): {result.state_probs[0]:.2%}")
        """
        ohlcv = np.asarray(ohlcv_data, dtype=float)
        if ohlcv.ndim != 2 or ohlcv.shape[1] != 5:
            raise ValueError(f"Expected shape (T, 5), got {ohlcv.shape}")
        if ohlcv.shape[0] < 60:
            raise ValueError(f"Need ≥60 observations, got {ohlcv.shape[0]}")

        # Compute log returns from close price (column 3)
        closes = ohlcv[:, 3]
        returns = np.diff(np.log(closes))

        # Re-fit HMM if requested
        if train:
            try:
                self.hmm_model.fit(returns)
            except Exception as e:
                raise RuntimeError(f"HMM fitting failed: {e}") from e

        # Run regime detection pipeline
        try:
            detection = detect_regime(returns, hmm=self.hmm_model)
        except Exception as e:
            raise RuntimeError(f"Regime detection failed: {e}") from e

        # Extract current state and probabilities
        current_state = int(detection.states[-1])
        state_probs = detection.posterior_probs[-1].astype(np.float32)

        # Current conditional volatility (annualized)
        current_vol = float(detection.conditional_vol[-1])

        # Volatility forecasts (5d and 21d ahead)
        vol_5d = detection.forecast_5d.astype(np.float32)
        vol_21d = detection.forecast_21d.astype(np.float32)

        inference = HMMGARCHInference(
            current_state=current_state,
            state_probs=state_probs,
            conditional_vol=current_vol,
            vol_forecast_5d=vol_5d,
            vol_forecast_21d=vol_21d,
            hmm_model=self.hmm_model,
            detection_result=detection,
        )
        self._current_inference = inference
        return inference

    def batch_predict(self, symbols_dict: dict[str, np.ndarray], train: bool = False) -> dict[str, HMMGARCHInference]:
        r"""
        Run parallel-ready batch predictions across multiple symbol time series.

        This method is asyncio-compatible for use in FastAPI endpoints. Predictions
        are independent and can be parallelized via asyncio.gather() or ThreadPoolExecutor.

        Args:
            symbols_dict: Dictionary mapping symbol names to OHLCV arrays.
                Each value is shape (T, 5) with [open, high, low, close, volume].
                Example: {"AAPL": ohlcv_aapl, "MSFT": ohlcv_msft}
            train: If True, re-fit HMM for each symbol. If False, use shared model.

        Returns:
            Dictionary mapping symbol → HMMGARCHInference predictions.

        Example:
            >>> symbols = {
            ...     "NIFTY50": nifty_ohlcv,
            ...     "BANKNIFTY": banknifty_ohlcv,
            ... }
            >>> results = engine.batch_predict(symbols, train=True)
            >>> for sym, pred in results.items():
            ...     print(f"{sym}: State {pred.current_state}, Vol {pred.conditional_vol:.2%}")
        """
        results: dict[str, HMMGARCHInference] = {}
        for symbol, ohlcv in symbols_dict.items():
            try:
                results[symbol] = self.predict(ohlcv, train=train)
            except Exception as e:
                # Log and continue with other symbols
                print(f"Warning: Prediction failed for {symbol}: {e}")
                continue
        return results

    def get_current_state(self) -> int | None:
        """Get the most recent state prediction (0=BULL, 1=BEAR, 2=SIDEWAYS, 3=CRISIS)."""
        return self._current_inference.current_state if self._current_inference else None

    def get_transition_matrix(self) -> np.ndarray | None:
        """
        Return the learned 4×4 transition matrix A.

        A[i, j] = P(s_{t+1} = j | s_t = i), representing regime persistence
        and switching probabilities.

        Returns:
            Array of shape (4, 4) with transition probabilities, or None if no inference yet.
        """
        return self.hmm_model.A_.copy() if hasattr(self.hmm_model, "A_") else None

    def get_state_statistics(self) -> dict[str, Any] | None:
        """
        Compute and return per-state statistics from the most recent detection.

        Returns a dictionary with keys like "state_0", "state_1", etc., containing:
            - avg_return: Mean log-return in that regime
            - avg_vol: Mean conditional volatility
            - frequency: Percentage of samples in that state
            - duration_days: Average consecutive days in that state

        Returns:
            Dict mapping state names to statistics, or None if no inference yet.

        Example output:
            {
                "state_0": {
                    "avg_return": 0.0012,
                    "avg_vol": 0.15,
                    "frequency": 0.35,
                    "duration_days": 8.2,
                },
                ...
            }
        """
        if not self._current_inference:
            return None

        dr = self._current_inference.detection_result
        states = dr.states
        n_states = self.hmm_model.n_states
        stats: dict[str, Any] = {}

        for k in range(n_states):
            mask = states == k
            n_in_state = np.sum(mask)

            if n_in_state > 0:
                avg_return = float(self.hmm_model.mu_[k])
                avg_vol = float(np.mean(dr.conditional_vol[mask]))
                freq = float(n_in_state / len(states))

                # Compute average duration via run-length encoding
                diffs = np.diff(np.concatenate(([n_states], states, [n_states])))
                transitions = np.where(diffs != 0)[0]
                durations = np.diff(transitions)
                kth_durations = durations[np.where(states[np.minimum(transitions[:-1], len(states) - 1)] == k)[0]]
                avg_duration = float(np.mean(kth_durations)) if len(kth_durations) > 0 else 1.0

                stats[f"state_{k}"] = {
                    "avg_return": avg_return,
                    "avg_vol": avg_vol,
                    "frequency": freq,
                    "duration_days": avg_duration,
                }

        return stats
