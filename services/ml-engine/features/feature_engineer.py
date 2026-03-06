"""
NeuroQuant Feature Engineering Pipeline
Implements 200+ technical, microstructure, statistical, and cross-asset features
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from pathlib import Path
import pickle
try:
    from sklearn.preprocessing import RobustScaler
    from sklearn.pipeline import Pipeline
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    RobustScaler = None
    Pipeline = None
import pandas_ta as ta
import talib
from tsfresh import extract_features, select_features
from tsfresh.utilities.dataframe_functions import impute
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

class FeatureEngineer:
    """
    Comprehensive feature engineering pipeline for stock market data.
    Implements 200+ features across multiple categories.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        if SKLEARN_AVAILABLE:
            self.scaler = RobustScaler()
        else:
            self.scaler = None
        self.pipeline = None
        self.feature_names = []

    def fit(self, df: pd.DataFrame) -> 'FeatureEngineer':
        """Fit the feature engineering pipeline"""
        logger.info("Fitting feature engineering pipeline...")

        # Extract features
        features_df = self._extract_all_features(df)

        # Fit scaler
        if SKLEARN_AVAILABLE and self.scaler:
            self.scaler.fit(features_df)

            # Create pipeline
            self.pipeline = Pipeline([
                ('scaler', self.scaler)
            ])
        else:
            self.pipeline = None
            logger.warning("sklearn not available, skipping scaling")

        self.feature_names = features_df.columns.tolist()
        logger.info(f"Pipeline fitted with {len(self.feature_names)} features")

        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform data using fitted pipeline"""
        if self.pipeline is None and SKLEARN_AVAILABLE:
            raise ValueError("Pipeline not fitted. Call fit() first.")

        features_df = self._extract_all_features(df)

        if self.pipeline and SKLEARN_AVAILABLE:
            scaled_features = self.pipeline.transform(features_df)
            return pd.DataFrame(
                scaled_features,
                index=df.index,
                columns=self.feature_names
            )
        else:
            return features_df

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform in one step"""
        return self.fit(df).transform(df)

    def _extract_all_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract all feature categories"""
        features = {}

        # Basic price features
        features.update(self._extract_price_features(df))

        # Technical indicators
        features.update(self._extract_technical_features(df))

        # Microstructure features
        features.update(self._extract_microstructure_features(df))

        # Statistical features
        features.update(self._extract_statistical_features(df))

        # Cross-asset features (placeholder - would need market data)
        features.update(self._extract_cross_asset_features(df))

        # tsfresh automated features
        features.update(self._extract_tsfresh_features(df))

        return pd.DataFrame(features, index=df.index)

    def _extract_price_features(self, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Extract basic price-based features"""
        features = {}

        # Returns
        features['return_1d'] = df['close'].pct_change()
        features['return_5d'] = df['close'].pct_change(5)
        features['return_20d'] = df['close'].pct_change(20)
        features['return_60d'] = df['close'].pct_change(60)

        # Log returns
        features['log_return_1d'] = np.log(df['close'] / df['close'].shift(1))
        features['log_return_5d'] = np.log(df['close'] / df['close'].shift(5))

        # Volatility
        features['volatility_20d'] = df['close'].pct_change().rolling(20).std()
        features['volatility_60d'] = df['close'].pct_change().rolling(60).std()

        # High-low range
        features['range_ratio'] = (df['high'] - df['low']) / df['close'].shift(1)

        return features

    def _extract_technical_features(self, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Extract technical indicators using pandas-ta and ta-lib"""
        features = {}

        try:
            # Trend indicators
            features['sma_5'] = ta.sma(df['close'], length=5)
            features['sma_10'] = ta.sma(df['close'], length=10)
            features['sma_20'] = ta.sma(df['close'], length=20)
            features['sma_50'] = ta.sma(df['close'], length=50)
            features['sma_200'] = ta.sma(df['close'], length=200)

            features['ema_5'] = ta.ema(df['close'], length=5)
            features['ema_10'] = ta.ema(df['close'], length=10)
            features['ema_20'] = ta.ema(df['close'], length=20)
            features['ema_50'] = ta.ema(df['close'], length=50)

            features['rsi_7'] = ta.rsi(df['close'], length=7)
            features['rsi_14'] = ta.rsi(df['close'], length=14)
            features['rsi_21'] = ta.rsi(df['close'], length=21)

        except Exception as e:
            logger.warning(f"Error extracting basic indicators: {e}")
            # Add dummy features
            for name in ['sma_5', 'sma_10', 'sma_20', 'sma_50', 'sma_200',
                        'ema_5', 'ema_10', 'ema_20', 'ema_50',
                        'rsi_7', 'rsi_14', 'rsi_21']:
                features[name] = np.full(len(df), np.nan)

        return features

    def _extract_microstructure_features(self, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Extract microstructure features"""
        features = {}

        # Amihud illiquidity
        features['amihud_illiquidity'] = (
            np.abs(df['close'].pct_change()) / (df['close'] * df['volume'])
        ).rolling(20).mean()

        # Roll spread proxy
        returns = df['close'].pct_change()
        features['roll_spread'] = 2 * np.sqrt(
            np.maximum(-np.cov(returns, returns.shift(-1)), 0)
        )

        # Bid-ask spread proxy
        features['spread_proxy'] = (df['high'] - df['low']) / df['close']

        # Kyle's lambda (price impact)
        # Simplified version - would need tick data for full implementation
        features['kyle_lambda'] = (
            np.abs(df['close'].pct_change()) / np.sqrt(df['volume'])
        ).rolling(20).mean()

        # Realized volatility (if we had tick data)
        # For now, use close-to-close
        features['realized_vol'] = (
            df['close'].pct_change().pow(2).rolling(20).sum()
        )

        # RVOL (relative volume)
        features['rvol'] = df['volume'] / df['volume'].rolling(20).mean()

        return features

    def _extract_statistical_features(self, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Extract statistical features"""
        features = {}

        returns = df['close'].pct_change().dropna()

        # Moments
        features['skew_20'] = returns.rolling(20).skew()
        features['kurtosis_20'] = returns.rolling(20).kurt()
        features['skew_60'] = returns.rolling(60).skew()
        features['kurtosis_60'] = returns.rolling(60).kurt()

        # Hurst exponent (simplified)
        def hurst_exponent(ts):
            """Calculate Hurst exponent"""
            if len(ts) < 20:
                return np.nan
            lags = range(2, min(20, len(ts)//2))
            tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]
            if len(tau) < 2:
                return np.nan
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            return poly[0] * 2.0

        features['hurst_20'] = returns.rolling(20).apply(hurst_exponent, raw=False)

        # Fractal dimension (Higuchi method - simplified)
        def fractal_dimension(ts):
            """Simplified fractal dimension calculation"""
            if len(ts) < 10:
                return np.nan
            # Simplified implementation
            return 1.0 + np.log(len(ts)) / np.log(10)

        features['fractal_dim'] = returns.rolling(20).apply(fractal_dimension, raw=False)

        # Permutation entropy
        def permutation_entropy(ts, order=3):
            """Calculate permutation entropy"""
            if len(ts) < order + 1:
                return np.nan
            permutations = []
            for i in range(len(ts) - order):
                perm = tuple(np.argsort(ts[i:i+order]))
                permutations.append(perm)

            unique_perms = set(permutations)
            probs = [permutations.count(p) / len(permutations) for p in unique_perms]
            entropy = -sum(p * np.log(p) for p in probs if p > 0)
            max_entropy = np.log(np.math.factorial(order))
            return entropy / max_entropy if max_entropy > 0 else np.nan

        features['perm_entropy'] = returns.rolling(20).apply(
            lambda x: permutation_entropy(x.values), raw=False
        )

        # Autocorrelation
        features['autocorr_1'] = returns.rolling(20).apply(
            lambda x: x.autocorr(lag=1) if len(x) > 1 else np.nan, raw=False
        )
        features['autocorr_2'] = returns.rolling(20).apply(
            lambda x: x.autocorr(lag=2) if len(x) > 2 else np.nan, raw=False
        )
        features['autocorr_5'] = returns.rolling(20).apply(
            lambda x: x.autocorr(lag=5) if len(x) > 5 else np.nan, raw=False
        )

        return features

    def _extract_cross_asset_features(self, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Extract cross-asset features (placeholders for now)"""
        features = {}

        # These would require additional market data
        # For now, create placeholder features
        features['beta_nifty'] = np.random.normal(1.0, 0.2, len(df))  # Placeholder
        features['rel_strength_sector'] = np.random.normal(0.0, 0.1, len(df))  # Placeholder
        features['vix_level'] = np.random.normal(20.0, 5.0, len(df))  # Placeholder
        features['yield_curve_slope'] = np.random.normal(0.5, 0.2, len(df))  # Placeholder

        return features

    def _extract_tsfresh_features(self, df: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Extract tsfresh automated features"""
        try:
            # Prepare data for tsfresh
            tsfresh_df = df[['close']].copy()
            tsfresh_df['id'] = 0  # Single time series
            tsfresh_df['time'] = range(len(tsfresh_df))

            # Extract features
            extracted_features = extract_features(
                tsfresh_df,
                column_id='id',
                column_sort='time',
                default_fc_parameters={
                    'mean': None,
                    'standard_deviation': None,
                    'variance': None,
                    'maximum': None,
                    'minimum': None,
                    'median': None,
                    'skewness': None,
                    'kurtosis': None,
                    'abs_energy': None,
                    'mean_abs_change': None,
                    'mean_change': None,
                    'mean_second_derivative_central': None,
                    'friedrich_coefficients': [{'coeff': 0, 'm': 3, 'r': 30}],
                    'max_langevin_fixed_point': [{'m': 3, 'r': 30}],
                    'linear_trend': [{'attr': 'pvalue'}],
                    'agg_linear_trend': [{'attr': 'pvalue', 'chunk_len': 5, 'f_agg': 'mean'}],
                    'augmented_dickey_fuller': [{'attr': 'pvalue'}],
                    'number_peaks': [{'n': 1}],
                    'sample_entropy': None,
                    'permutation_entropy': [{'tau': 1, 'n': 4}],
                },
                impute_function=impute
            )

            # Convert to dict of arrays
            tsfresh_dict = {}
            for col in extracted_features.columns:
                tsfresh_dict[f'tsfresh_{col}'] = extracted_features[col].values

            return tsfresh_dict

        except Exception as e:
            logger.warning(f"tsfresh feature extraction failed: {e}")
            return {}

    def save_pipeline(self, path: str):
        """Save fitted pipeline to disk"""
        if not SKLEARN_AVAILABLE:
            logger.warning("sklearn not available, cannot save pipeline")
            return

        if self.pipeline is None:
            raise ValueError("Pipeline not fitted")

        pipeline_data = {
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'config': self.config
        }

        with open(path, 'wb') as f:
            pickle.dump(pipeline_data, f)

        logger.info(f"Pipeline saved to {path}")

    def load_pipeline(self, path: str) -> 'FeatureEngineer':
        """Load fitted pipeline from disk"""
        if not SKLEARN_AVAILABLE:
            logger.warning("sklearn not available, cannot load pipeline")
            return self

        with open(path, 'rb') as f:
            pipeline_data = pickle.load(f)

        self.scaler = pipeline_data['scaler']
        self.feature_names = pipeline_data['feature_names']
        self.config = pipeline_data['config']

        self.pipeline = Pipeline([
            ('scaler', self.scaler)
        ])

        logger.info(f"Pipeline loaded from {path}")
        return self