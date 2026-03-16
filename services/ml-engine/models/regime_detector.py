"""
HMM Regime Detection Model
Detects market regimes (bull, bear, sideways) using Hidden Markov Models
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import logging
from hmmlearn import hmm
from sklearn.preprocessing import StandardScaler
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)


class RegimeDetector:
    """
    Hidden Markov Model for market regime detection.
    States: 0=Bear, 1=Sideways, 2=Bull
    """

    def __init__(self, n_states: int = 3, random_state: int = 42):
        self.n_states = n_states
        self.random_state = random_state
        self.model = None
        self.scaler = StandardScaler()
        self.is_fitted = False

    def fit(self, returns: pd.Series, features: Optional[pd.DataFrame] = None) -> 'RegimeDetector':
        """Fit HMM on historical returns data."""
        logger.info("Fitting HMM regime detector...")

        # Prepare features
        if features is None:
            # Use returns and volatility as features
            vol_20 = returns.rolling(20).std()
            vol_60 = returns.rolling(60).std()
            features = pd.DataFrame({
                'returns': returns,
                'vol_20': vol_20,
                'vol_60': vol_60,
                'returns_ma_5': returns.rolling(5).mean(),
                'returns_ma_20': returns.rolling(20).mean(),
            }).dropna()

        # Scale features
        scaled_features = self.scaler.fit_transform(features.values)

        # Fit HMM
        self.model = hmm.GaussianHMM(
            n_components=self.n_states,
            covariance_type="full",
            random_state=self.random_state,
            n_iter=1000
        )

        self.model.fit(scaled_features)
        self.is_fitted = True

        # Log state means (for interpretation)
        state_means = self.model.means_
        logger.info(f"HMM fitted with {self.n_states} states")
        for i, mean in enumerate(state_means):
            logger.info(f"State {i} mean returns: {mean[0]:.4f}")

        return self

    def predict(self, returns: pd.Series, features: Optional[pd.DataFrame] = None) -> np.ndarray:
        """Predict regime states for new data."""
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")

        # Prepare features
        if features is None:
            vol_20 = returns.rolling(20).std()
            vol_60 = returns.rolling(60).std()
            features = pd.DataFrame({
                'returns': returns,
                'vol_20': vol_20,
                'vol_60': vol_60,
                'returns_ma_5': returns.rolling(5).mean(),
                'returns_ma_20': returns.rolling(20).mean(),
            }).dropna()

        # Scale features
        scaled_features = self.scaler.transform(features.values)

        # Predict states
        states = self.model.predict(scaled_features)

        return states

    def predict_proba(self, returns: pd.Series, features: Optional[pd.DataFrame] = None) -> np.ndarray:
        """Predict regime state probabilities."""
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() first.")

        # Prepare features
        if features is None:
            vol_20 = returns.rolling(20).std()
            vol_60 = returns.rolling(60).std()
            features = pd.DataFrame({
                'returns': returns,
                'vol_20': vol_20,
                'vol_60': vol_60,
                'returns_ma_5': returns.rolling(5).mean(),
                'returns_ma_20': returns.rolling(20).mean(),
            }).dropna()

        # Scale features
        scaled_features = self.scaler.transform(features.values)

        # Predict state probabilities
        state_probs = self.model.predict_proba(scaled_features)

        return state_probs

    def get_regime_labels(self, states: np.ndarray) -> List[str]:
        """Convert state numbers to regime labels based on mean returns."""
        if not self.is_fitted:
            return ['unknown'] * len(states)

        # Sort states by mean returns: lowest = bear, middle = sideways, highest = bull
        state_means = self.model.means_[:, 0]  # Returns are first feature
        sorted_indices = np.argsort(state_means)

        state_map = {
            sorted_indices[0]: 'bear',      # Lowest returns
            sorted_indices[1]: 'sideways',  # Middle returns
            sorted_indices[2]: 'bull'       # Highest returns
        }

        return [state_map[state] for state in states]

    def save_model(self, path: str):
        """Save fitted model to disk."""
        if not self.is_fitted:
            raise ValueError("Model not fitted")

        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'n_states': self.n_states,
            'random_state': self.random_state,
            'is_fitted': self.is_fitted
        }

        with open(path, 'wb') as f:
            pickle.dump(model_data, f)

        logger.info(f"Regime detector saved to {path}")

    def load_model(self, path: str) -> 'RegimeDetector':
        """Load fitted model from disk."""
        with open(path, 'rb') as f:
            model_data = pickle.load(f)

        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.n_states = model_data['n_states']
        self.random_state = model_data['random_state']
        self.is_fitted = model_data['is_fitted']

        logger.info(f"Regime detector loaded from {path}")
        return self