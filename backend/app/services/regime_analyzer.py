"""Regime Analysis — GARCH Volatility and HMM Regime modeling."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class GARCHVolatilityModel:
    """GARCH(1,1) model for conditional volatility forecasting."""

    def __init__(self) -> None:
        self.model = None
        self.result = None

    def fit(self, returns: pd.Series) -> None:
        """Fit a GARCH(1,1) model to the log returns.

        Args:
            returns: Pandas Series of daily log returns (percentage, e.g. 0.01 * 100 = 1.0).
                     Arch model works best with scaled returns (e.g. multiplied by 100).
        """
        try:
            from arch import arch_model

            # Drop NaN and scale to percentage for optimizer stability
            valid_returns = returns.dropna() * 100.0

            if len(valid_returns) < 50:
                logger.warning("Not enough data to fit GARCH securely. Needed 50, got %s", len(valid_returns))
                return

            self.model = arch_model(valid_returns, vol="Garch", p=1, q=1, rescale=False)
            self.result = self.model.fit(disp="off", show_warning=False)
        except ImportError:
            logger.error("arch package is not installed. Run `pip install arch`.")
        except Exception as e:
            logger.error(f"GARCH fitting failed: {e}")

    def forecast(self, horizon: int = 1) -> list[float]:
        """Forecast conditional volatility for the next `horizon` days.

        Returns:
            List of annualized conditional volatility forecasts (as decimals, e.g., 0.15 for 15%).
        """
        if self.result is None:
            return [0.0] * horizon

        try:
            forecasts = self.result.forecast(horizon=horizon)
            # The forecast variance is for the scaled returns.
            # We divide by 10000 to get back to decimal variance, then sqrt, then annualize (sqrt(252))
            var_forecast = forecasts.variance.iloc[-1].values
            vol_forecast_daily = np.sqrt(var_forecast / 10000.0)
            vol_forecast_annual = vol_forecast_daily * np.sqrt(252)
            return vol_forecast_annual.tolist()
        except Exception as e:
            logger.error(f"GARCH forecasting failed: {e}")
            return [0.0] * horizon

    def save_model(self, filepath: str) -> None:
        """Save the fitted GARCH model result using joblib."""
        import os

        import joblib
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(self.result, filepath)

    def load_model(self, filepath: str) -> None:
        """Load a fitted GARCH model result using joblib."""
        import joblib
        self.result = joblib.load(filepath)



class HMMRegimeModel:
    """Hidden Markov Model for market regime detection."""

    def __init__(self, n_states: int = 3) -> None:
        """Initialize the HMM model.

        Args:
            n_states: Number of regimes. Default 3 (Bull, Bear, Sideways).
        """
        self.n_states = n_states
        self.model = None

    def fit(self, features: pd.DataFrame) -> None:
        """Fit the GaussianHMM to the features (returns, volatility)."""
        try:
            from hmmlearn.hmm import GaussianHMM

            valid_features = features.dropna()
            if len(valid_features) < 100:
                logger.warning("Not enough data to fit HMM securely.")
                return

            # We use a Gaussian HMM with diag covariance to avoid singularity issues
            self.model = GaussianHMM(
                n_components=self.n_states,
                covariance_type="diag",
                n_iter=100,
                random_state=42,
            )
            self.model.fit(valid_features.values)
        except ImportError:
            logger.error("hmmlearn package is not installed. Run `pip install hmmlearn`.")
        except Exception as e:
            logger.error(f"HMM fitting failed: {e}")

    def predict(self, features: pd.DataFrame) -> tuple[int, list[float]]:
        """Predict the current regime state and probabilities.

        Returns:
            Tuple of (viterbi_state, state_probabilities)
        """
        if self.model is None or features.empty:
            return (0, [0.0] * self.n_states)

        try:
            # We only want to predict the state of the *last* observation based on the sequence
            valid_features = features.dropna()
            if valid_features.empty:
                 return (0, [0.0] * self.n_states)

            # Predict most likely sequence of states
            hidden_states = self.model.predict(valid_features.values)
            last_state = int(hidden_states[-1])

            # Predict probabilities
            probs = self.model.predict_proba(valid_features.values)
            last_probs = probs[-1].tolist()

            return last_state, last_probs
        except Exception as e:
            logger.error(f"HMM prediction failed: {e}")
            return (0, [0.0] * self.n_states)

    def map_states_to_labels(self, features: pd.DataFrame) -> dict[int, str]:
        """Heuristically map HMM integer states to semantic labels.

        This aligns state 0 to Bull, 1 to Bear, 2 to Sideways based on the
        mean return and variance of the states.
        """
        if self.model is None:
            return {0: "bull", 1: "bear", 2: "sideways"}

        # Extract the means for the first feature (which should be returns)
        # and the second feature (which should be volatility)
        means = self.model.means_

        # Calculate a simple score: return - volatility
        # Highest score -> Bull
        # Lowest score -> Bear
        # Middle -> Sideways
        scores = []
        for i in range(self.n_states):
            ret_mean = means[i][0]
            vol_mean = means[i][1] if len(means[i]) > 1 else 0
            scores.append((i, ret_mean - 0.5 * vol_mean))

        scores.sort(key=lambda x: x[1], reverse=True)

        mapping = {}
        if self.n_states >= 1:
            mapping[scores[0][0]] = "bull"
        if self.n_states >= 2:
            mapping[scores[-1][0]] = "bear"
        if self.n_states >= 3:
            mapping[scores[1][0]] = "sideways"

        return mapping

    def save_model(self, filepath: str) -> None:
        """Save the fitted HMM model using joblib."""
        import os

        import joblib
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(self.model, filepath)

    def load_model(self, filepath: str) -> None:
        """Load a fitted HMM model using joblib."""
        import joblib
        self.model = joblib.load(filepath)
