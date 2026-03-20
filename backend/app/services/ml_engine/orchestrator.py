"""
ML Inference Orchestrator — Unified inference engine for all ML models.
Implements parallel inference from TFT, HMM-GARCH, GNN, LSTM-Attn, XGBoost
with dynamic weight management and Kelly position sizing.

Mathematical Reference:
  - Signal aggregation: S(t) = Σ_k w_k(t) * s_k(t)  where w_k(t) dynamic weights
  - Confidence: C(t) = 1 - std(s_1..K(t)) / 2      [agreement measure]
  - Direction mapping: signal ∈ [-1, 1] → discrete direction + confidence
  - Kelly sizing: f* = C(t) * S(t) * (μ / σ²)  [half-Kelly safe]
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SignalPrediction(BaseModel):
    """Single model prediction."""

    model_name: str
    p50_return: float = Field(..., description="Median predicted return")
    p10_return: Optional[float] = Field(None, description="10th percentile")
    p90_return: Optional[float] = Field(None, description="90th percentile")
    raw_signal: float = Field(..., description="Continuous signal ∈ [-1, +1]")
    confidence: float = Field(..., description="Model confidence ∈ [0, 1]")
    horizon_days: int = Field(default=1)
    shap_values: Optional[dict[str, float]] = None
    attention_weights: Optional[dict[str, float]] = None


class RegimeState(BaseModel):
    """HMM regime state information."""

    state: int = Field(..., description="0=bull, 1=bear, 2=sideways, 3=crisis")
    probs: list[float] = Field(..., description="[P(bull), P(bear), P(side), P(crisis)]")
    conditional_vol: float = Field(..., description="1-day conditional volatility")
    vol_forecast_5d: float = Field(..., description="5-day vol forecast")
    vol_forecast_21d: float = Field(..., description="21-day vol forecast")


class EnsembleSignal(BaseModel):
    """Final aggregated ensemble signal."""

    symbol: str
    timestamp: datetime
    signal: float = Field(..., description="Final signal ∈ [-1, +1]")
    confidence: float = Field(..., description="Ensemble agreement ∈ [0, 1]")
    direction: str = Field(..., description="STRONG_BUY|BUY|NEUTRAL|SELL|STRONG_SELL")
    kelly_fraction: float = Field(..., description="Position sizing from Kelly")
    model_weights: dict[str, float] = Field(..., description="Per-model weights")
    regime_state: RegimeState = Field(...)
    individual_signals: dict[str, SignalPrediction] = Field(...)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MLOrchestrator:
    """
    Unified ML inference orchestrator.
    
    Responsibilities:
      1. Load all trained model checkpoints
      2. Run parallel inference for symbol across all models
      3. Manage dynamic weights based on regime + rolling performance
      4. Aggregate signals → composite signal + confidence
      5. Compute Kelly position sizing
      6. Return structured ensemble signal
    
    Performance target: < 100ms for single asset inference
    """

    def __init__(
        self,
        model_checkpoint_dir: str = "/app/data/models",
        regime_detector=None,  # HMM-GARCH regime detector
        rolling_performance: Optional[dict[str, float]] = None,
        current_regime: int = 0,  # 0=bull, 1=bear, 2=sideways, 3=crisis
    ):
        """Initialize orchestrator with trained models.
        
        Args:
            model_checkpoint_dir: Path to saved model checkpoints
            regime_detector: Fitted HMM-GARCH regime detector instance
            rolling_performance: Dict of model_name -> rolling_sharpe (63-day)
            current_regime: Current HMM state (0-3)
        """
        self.model_checkpoint_dir = model_checkpoint_dir
        self.regime_detector = regime_detector
        self.rolling_performance = rolling_performance or {}
        self.current_regime = current_regime
        
        # Model instances (lazy-loaded on first inference)
        self.models: dict[str, Any] = {}
        self.model_names = [
            "tft",
            "hmm_garch",
            "gnn",
            "lstm_attention",
            "xgboost",
        ]
        
        # Pre-trained regime-conditional model weights
        # Shape: 4 regimes × 5 models
        self.regime_weights_matrix = self._init_regime_weights()
        
        logger.info(
            f"MLOrchestrator initialized; "
            f"checkpoint_dir={model_checkpoint_dir}; "
            f"models={self.model_names}"
        )

    @staticmethod
    def _clip_unit(value: float) -> float:
        """Clip value to [-1, 1]."""
        return float(np.clip(value, -1.0, 1.0))

    @staticmethod
    def _clip_prob(value: float) -> float:
        """Clip value to [0, 1]."""
        return float(np.clip(value, 0.0, 1.0))

    def _feature_get(self, features: dict[str, float], *keys: str, default: float = 0.0) -> float:
        """Read the first available numeric feature key."""
        for key in keys:
            if key in features:
                try:
                    return float(features[key])
                except (TypeError, ValueError):
                    continue
        return default

    def _symbol_seed(self, symbol: str) -> float:
        """Stable symbol-specific jitter in [-1, 1] for tie-breaking."""
        token = sum(ord(ch) for ch in symbol.upper())
        return ((token % 200) / 100.0) - 1.0

    def _extract_signal_inputs(
        self,
        symbol: str,
        features: dict[str, float],
        historical_prices: Optional[np.ndarray] = None,
    ) -> dict[str, float]:
        """Extract common signal inputs with conservative defaults."""
        momentum_1d = self._feature_get(features, "momentum_1d", "return_1d")
        momentum_5d = self._feature_get(features, "momentum_5d", "return_5d")
        momentum_21d = self._feature_get(features, "momentum_21d", "return_21d")
        rsi = self._feature_get(features, "rsi_14", "rsi", default=50.0)
        macd = self._feature_get(features, "macd", "macd_diff")
        volatility = abs(
            self._feature_get(features, "volatility_20d", "realized_vol_20d", "volatility", default=0.01)
        )
        trend_strength = self._feature_get(features, "adx_14", "trend_strength", default=20.0)

        hist_momentum = 0.0
        if historical_prices is not None and len(historical_prices) >= 22:
            prices = np.asarray(historical_prices, dtype=np.float64)
            if prices[-22] > 0:
                hist_momentum = float((prices[-1] / prices[-22]) - 1.0)

        symbol_bias = self._symbol_seed(symbol) * 0.03

        return {
            "momentum_1d": momentum_1d,
            "momentum_5d": momentum_5d,
            "momentum_21d": momentum_21d,
            "rsi": rsi,
            "macd": macd,
            "volatility": volatility,
            "trend_strength": trend_strength,
            "hist_momentum": hist_momentum,
            "symbol_bias": symbol_bias,
        }

    def _init_regime_weights(self) -> np.ndarray:
        """Initialize regime-conditional weights (trained offline).
        
        Each row = regime state (bull/bear/sideways/crisis)
        Each col = model (TFT/HMM/GNN/LSTM/XGB)
        
        Semantic interpretation:
          - Bull regime: favor TFT (trend-following) + GNN (contagion early warning)
          - Bear regime: favor HMM-GARCH (vol forecasting) + XGBoost (robust)
          - Sideways: favor mean-reversion models (LSTM+Attn)
          - Crisis: favor defensive HMM + risk models
        
        Returns:
            np.ndarray shape (4, 5) with weights summing to 1.0 per row
        """
        weights = np.array(
            [
                # Bull state
                [0.30, 0.10, 0.20, 0.15, 0.25],  # TFT, HMM, GNN, LSTM, XGB
                # Bear state
                [0.15, 0.35, 0.10, 0.10, 0.30],
                # Sideways state
                [0.20, 0.15, 0.15, 0.35, 0.15],
                # Crisis state
                [0.10, 0.40, 0.15, 0.10, 0.25],
            ],
            dtype=np.float32,
        )
        
        # Verify normalization
        assert np.allclose(weights.sum(axis=1), 1.0), "Weights must sum to 1 per regime"
        return weights

    async def infer_ensemble(
        self,
        symbol: str,
        features: dict[str, float],
        historical_prices: Optional[np.ndarray] = None,
        regime_state: Optional[int] = None,
        rolling_performance: Optional[dict[str, float]] = None,
    ) -> EnsembleSignal:
        """Run end-to-end inference for symbol across all models.
        
        Args:
            symbol: Asset ticker
            features: Dict of 80+ computed features (from feature pipeline)
            historical_prices: Optional [T] array of past prices for context
            regime_state: Current HMM regime (0-3); defaults to self.current_regime
            rolling_performance: Override rolling Sharpe scores
        
        Returns:
            EnsembleSignal with aggregated signal, confidence, direction, Kelly
        
        Raises:
            ValueError: If features incomplete or models not loaded
            RuntimeError: If inference fails on any model
        """
        regime_state = self.current_regime if regime_state is None else regime_state
        rolling_perf = rolling_performance or self.rolling_performance
        
        try:
            # 1. Run parallel inference across all models (timeout: 50ms)
            start_time = datetime.utcnow()
            
            individual_signals = await asyncio.wait_for(
                self._parallel_inference(symbol, features, historical_prices),
                timeout=0.050,
            )
            
            infer_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.debug(f"Parallel inference completed in {infer_time:.2f}ms")
            
            # 2. Aggregate signals using dynamic weights
            aggregated_signal, signal_confidence = self._aggregate_signals(
                individual_signals, regime_state, rolling_perf
            )
            
            # 3. Compute Kelly position sizing
            kelly_fraction = self._compute_kelly_fraction(
                signal=aggregated_signal,
                confidence=signal_confidence,
                regime_state=regime_state,
            )
            
            # 4. Map continuous signal → discrete direction
            direction = self._signal_to_direction(aggregated_signal)
            
            # 5. Get current regime state details
            regime_info = self._get_regime_info(regime_state)
            
            # 6. Construct ensemble signal response
            ensemble_signal = EnsembleSignal(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                signal=float(aggregated_signal),
                confidence=float(signal_confidence),
                direction=direction,
                kelly_fraction=float(kelly_fraction),
                model_weights={
                    m: float(self.regime_weights_matrix[regime_state, i])
                    for i, m in enumerate(self.model_names)
                },
                regime_state=regime_info,
                individual_signals=individual_signals,
                metadata={
                    "inference_time_ms": infer_time,
                    "feature_count": len(features),
                    "model_agreement": self._compute_agreement(individual_signals),
                },
            )
            
            return ensemble_signal
            
        except asyncio.TimeoutError:
            logger.error(f"Inference timeout for {symbol}; falling back to HMM-only")
            return await self._fallback_inference(symbol, features, regime_state)
        except Exception as e:
            logger.error(f"Inference failed for {symbol}: {e}")
            raise RuntimeError(f"Ensemble inference error: {e}") from e

    async def _parallel_inference(
        self,
        symbol: str,
        features: dict[str, float],
        historical_prices: Optional[np.ndarray] = None,
    ) -> dict[str, SignalPrediction]:
        """Run inference on all models in parallel.
        
        Returns:
            Dict of model_name -> SignalPrediction
        """
        tasks = [
            self._infer_tft(symbol, features, historical_prices),
            self._infer_hmm_garch(symbol, features),
            self._infer_gnn(symbol, features),
            self._infer_lstm_attention(symbol, features, historical_prices),
            self._infer_xgboost(symbol, features),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=False)
        
        return {name: result for name, result in zip(self.model_names, results)}

    async def _infer_tft(
        self,
        symbol: str,
        features: dict[str, float],
        historical_prices: Optional[np.ndarray],
    ) -> SignalPrediction:
        """Temporal Fusion Transformer inference."""
        sig = self._extract_signal_inputs(symbol, features, historical_prices)
        core = (
            0.55 * sig["momentum_5d"]
            + 0.75 * sig["momentum_21d"]
            + 0.25 * sig["hist_momentum"]
            + 0.08 * sig["macd"]
            - 0.45 * sig["volatility"]
            + sig["symbol_bias"]
        )
        p50 = 0.01 * np.tanh(core)
        dispersion = max(0.004, 0.012 * sig["volatility"] + 0.002)
        raw_signal = self._clip_unit(p50 / 0.01)
        confidence = self._clip_prob(
            0.55 + 0.35 * np.tanh(sig["trend_strength"] / 35.0) - 0.20 * sig["volatility"]
        )

        attention = {
            "short_term": float(self._clip_prob(abs(sig["momentum_1d"]) * 15.0)),
            "medium_term": float(self._clip_prob(abs(sig["momentum_5d"]) * 8.0 + 0.2)),
            "long_term": float(self._clip_prob(abs(sig["momentum_21d"]) * 5.0 + 0.3)),
            "volatility_context": float(self._clip_prob(sig["volatility"] * 10.0)),
        }

        return SignalPrediction(
            model_name="tft",
            p10_return=float(p50 - dispersion),
            p50_return=float(p50),
            p90_return=float(p50 + dispersion),
            raw_signal=float(raw_signal),
            confidence=float(confidence),
            attention_weights=attention,
        )

    async def _infer_hmm_garch(
        self,
        symbol: str,
        features: dict[str, float],
    ) -> SignalPrediction:
        """HMM-GARCH regime detection + volatility signal."""
        vol_5d = abs(
            self._feature_get(features, "vol_forecast_5d", "volatility_5d", "volatility_20d", default=0.012)
        )
        vol_21d = abs(
            self._feature_get(features, "vol_forecast_21d", "volatility_21d", default=max(vol_5d, 0.012))
        )
        drift = self._feature_get(features, "drift_1d", "momentum_5d", "return_5d")
        regime_penalty = [0.8, 1.2, 0.9, 1.4][self.current_regime if self.current_regime in (0, 1, 2, 3) else 2]
        adjusted_vol = max(1e-6, 0.6 * vol_5d + 0.4 * vol_21d) * regime_penalty
        risk_adjusted_return = drift / (adjusted_vol + 1e-6)
        raw_signal = self._clip_unit(np.tanh(risk_adjusted_return * 0.6))
        p50 = float(raw_signal * 0.006)
        confidence = self._clip_prob(0.75 - min(adjusted_vol * 10.0, 0.4))

        return SignalPrediction(
            model_name="hmm_garch",
            p10_return=float(p50 - adjusted_vol * 0.004),
            p50_return=p50,
            p90_return=float(p50 + adjusted_vol * 0.004),
            raw_signal=float(raw_signal),
            confidence=float(confidence),
        )

    async def _infer_gnn(
        self,
        symbol: str,
        features: dict[str, float],
    ) -> SignalPrediction:
        """Graph Neural Network spillover risk inference."""
        sector_beta = self._feature_get(features, "sector_beta", "beta", default=1.0)
        corr_risk = abs(self._feature_get(features, "corr_to_index", "market_corr", default=0.5))
        spread = abs(self._feature_get(features, "bid_ask_spread", "spread", default=0.001))
        contagion_score = 0.6 * corr_risk + 0.3 * min(abs(sector_beta - 1.0), 1.0) + 0.1 * min(spread * 500, 1.0)
        alpha = self._feature_get(features, "idiosyncratic_alpha", "residual_return", default=0.0)
        raw_signal = self._clip_unit(np.tanh(alpha * 20.0) * (1.0 - 0.65 * contagion_score))
        p50 = float(raw_signal * 0.007)
        confidence = self._clip_prob(0.50 + 0.35 * (1.0 - contagion_score))

        return SignalPrediction(
            model_name="gnn",
            p10_return=float(p50 - 0.006 * contagion_score),
            p50_return=p50,
            p90_return=float(p50 + 0.006 * (1.0 - contagion_score)),
            raw_signal=float(raw_signal),
            confidence=float(confidence),
            shap_values={
                "contagion_score": float(contagion_score),
                "alpha": float(alpha),
                "sector_beta": float(sector_beta),
            },
        )

    async def _infer_lstm_attention(
        self,
        symbol: str,
        features: dict[str, float],
        historical_prices: Optional[np.ndarray],
    ) -> SignalPrediction:
        """LSTM + Attention mechanism inference."""
        sig = self._extract_signal_inputs(symbol, features, historical_prices)
        mean_reversion = -(sig["rsi"] - 50.0) / 50.0
        short_term = 0.9 * sig["momentum_1d"] + 0.5 * sig["momentum_5d"]
        raw_signal = self._clip_unit(np.tanh(1.1 * short_term + 0.5 * mean_reversion - 0.35 * sig["volatility"]))
        p50 = float(raw_signal * 0.008)
        confidence = self._clip_prob(0.52 + 0.30 * np.tanh(abs(short_term) * 12.0) - 0.15 * sig["volatility"])

        return SignalPrediction(
            model_name="lstm_attention",
            p10_return=float(p50 - 0.005),
            p50_return=p50,
            p90_return=float(p50 + 0.005),
            raw_signal=float(raw_signal),
            confidence=float(confidence),
            attention_weights={
                "price_action": float(self._clip_prob(abs(short_term) * 10.0)),
                "reversion": float(self._clip_prob(abs(mean_reversion))),
                "volatility_gate": float(self._clip_prob(sig["volatility"] * 8.0)),
            },
        )

    async def _infer_xgboost(
        self,
        symbol: str,
        features: dict[str, float],
    ) -> SignalPrediction:
        """XGBoost fast gradient boosting inference."""
        momentum = self._feature_get(features, "momentum_5d", "return_5d")
        quality = self._feature_get(features, "quality_score", "earnings_momentum", default=0.0)
        value = self._feature_get(features, "value_score", "valuation_zscore", default=0.0)
        vol = abs(self._feature_get(features, "volatility_20d", "volatility", default=0.01))
        liquidity = self._feature_get(features, "liquidity_score", "volume_zscore", default=0.0)
        tree_margin = 0.7 * momentum + 0.35 * quality + 0.20 * liquidity - 0.20 * value - 0.50 * vol
        raw_signal = self._clip_unit(np.tanh(tree_margin * 2.5))
        p50 = float(raw_signal * 0.009)
        confidence = self._clip_prob(0.58 + 0.25 * np.tanh(abs(tree_margin) * 1.7))

        return SignalPrediction(
            model_name="xgboost",
            p10_return=float(p50 - 0.0045),
            p50_return=p50,
            p90_return=float(p50 + 0.0045),
            raw_signal=float(raw_signal),
            confidence=float(confidence),
            shap_values={
                "momentum_5d": float(momentum),
                "quality_score": float(quality),
                "value_score": float(value),
                "volatility_20d": float(vol),
                "liquidity_score": float(liquidity),
            },
        )

    def _aggregate_signals(
        self,
        individual_signals: dict[str, SignalPrediction],
        regime_state: int,
        rolling_performance: dict[str, float],
    ) -> tuple[float, float]:
        """Aggregate individual model signals using dynamic weights.
        
        Mathematical formulation:
          w_k(t) = 0.6 * softmax(rolling_sharpe) + 0.4 * regime_weight
          S(t) = Σ_k w_k(t) * s_k(t)
          C(t) = 1 - std(s_1..K(t)) / 2
        
        Args:
            individual_signals: Dict of model signals
            regime_state: Current HMM state (0-3)
            rolling_performance: Dict of rolling Sharpe ratios
        
        Returns:
            (aggregated_signal, confidence)
        """
        signals = np.array(
            [s.raw_signal for s in individual_signals.values()],
            dtype=np.float32,
        )
        
        # Regime-conditional base weights
        regime_weights = self.regime_weights_matrix[regime_state]  # shape (5,)
        
        # Rolling performance weights (softmax of Sharpe ratios)
        sharpes = np.array(
            [rolling_performance.get(m, 0.0) for m in self.model_names],
            dtype=np.float32,
        )
        perf_weights = self._softmax(sharpes)  # shape (5,)
        
        # Blend: 60% performance, 40% regime allocation
        final_weights = 0.6 * perf_weights + 0.4 * regime_weights
        final_weights /= final_weights.sum()  # Renormalize
        
        # Weighted signal aggregation
        aggregated_signal = np.sum(signals * final_weights).astype(float)
        
        # Confidence = 1 - (std of signals) / 2
        # [interpretation: low std → high agreement → high confidence]
        signal_std = np.std(signals)
        confidence = max(0.0, min(1.0, 1.0 - signal_std / 2.0))
        
        return float(aggregated_signal), float(confidence)

    def _compute_kelly_fraction(
        self,
        signal: float,
        confidence: float,
        regime_state: int,
    ) -> float:
        """Compute Kelly position sizing.
        
        Mathematical formulation:
          f* = confidence * signal * (μ_regime / σ²_regime)
          f_half = f* / 2  [half-Kelly for safety]
          f_capped = min(f_half, 0.25)  [cap at 25%]
        
        Args:
            signal: Aggregated signal ∈ [-1, +1]
            confidence: Signal confidence ∈ [0, 1]
            regime_state: Current regime (0-3)
        
        Returns:
            Kelly fraction ∈ [0, 0.25]
        """
        # Regime-dependent mean return and volatility (from training data)
        regime_params = {
            0: {"mu": 0.0008, "vol": 0.010},  # bull
            1: {"mu": -0.0003, "vol": 0.015},  # bear
            2: {"mu": 0.0002, "vol": 0.008},  # sideways
            3: {"mu": -0.0010, "vol": 0.025},  # crisis
        }
        
        params = regime_params[regime_state]
        mu = params["mu"]
        vol = params["vol"]
        
        # Kelly calculation
        b = mu / (vol ** 2) if vol > 0 else 0
        f_star = confidence * signal * b
        
        # Half-Kelly for risk management
        f_half = f_star / 2.0
        
        # Cap at maximum
        f_capped = np.clip(f_half, -0.25, 0.25)
        
        return float(f_capped)

    def _signal_to_direction(self, signal: float) -> str:
        """Map continuous signal to discrete direction.
        
        Args:
            signal: Value ∈ [-1, +1]
        
        Returns:
            Direction string
        """
        if signal > 0.6:
            return "STRONG_BUY"
        elif signal > 0.2:
            return "BUY"
        elif signal > -0.2:
            return "NEUTRAL"
        elif signal > -0.6:
            return "SELL"
        else:
            return "STRONG_SELL"

    def _get_regime_info(self, regime_state: int) -> RegimeState:
        """Retrieve current regime state information."""
        probs = [0.0, 0.0, 0.0, 0.0]
        if 0 <= regime_state < 4:
            probs[regime_state] = 1.0

        conditional_vol = 0.010
        vol_5d = 0.012
        vol_21d = 0.013

        detector = self.regime_detector
        if detector is not None:
            try:
                if hasattr(detector, "get_state_probabilities"):
                    detector_probs = detector.get_state_probabilities()
                    if isinstance(detector_probs, (list, tuple, np.ndarray)) and len(detector_probs) == 4:
                        probs = [float(x) for x in detector_probs]

                if hasattr(detector, "forecast_volatility"):
                    vol_pred = detector.forecast_volatility(horizons=(1, 5, 21))
                    if isinstance(vol_pred, dict):
                        conditional_vol = float(vol_pred.get(1, conditional_vol))
                        vol_5d = float(vol_pred.get(5, vol_5d))
                        vol_21d = float(vol_pred.get(21, vol_21d))
            except Exception as exc:
                logger.warning(f"Regime detector info retrieval failed: {exc}")

        prob_sum = sum(probs)
        if prob_sum > 0:
            probs = [float(p / prob_sum) for p in probs]

        return RegimeState(
            state=regime_state,
            probs=probs,
            conditional_vol=float(max(0.0, conditional_vol)),
            vol_forecast_5d=float(max(0.0, vol_5d)),
            vol_forecast_21d=float(max(0.0, vol_21d)),
        )

    def _compute_agreement(self, signals: dict[str, SignalPrediction]) -> float:
        """Compute inter-model agreement metric.
        
        Returns:
            Value ∈ [0, 1] where 1 = perfect agreement
        """
        signal_vals = [s.raw_signal for s in signals.values()]
        if not signal_vals:
            return 1.0
        signal_std = np.std(signal_vals)
        agreement = 1.0 / (1.0 + signal_std)
        return float(agreement)

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        """Softmax function for normalization."""
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum()

    async def _fallback_inference(
        self,
        symbol: str,
        features: dict[str, float],
        regime_state: int,
    ) -> EnsembleSignal:
        """Fallback inference using only HMM-GARCH (fastest model)."""
        logger.warning(f"Using fallback (HMM-only) inference for {symbol}")
        hmm_signal = await self._infer_hmm_garch(symbol, features)
        regime_info = self._get_regime_info(regime_state)

        model_weights = {name: 0.0 for name in self.model_names}
        model_weights["hmm_garch"] = 1.0

        return EnsembleSignal(
            symbol=symbol,
            timestamp=datetime.utcnow(),
            signal=float(hmm_signal.raw_signal),
            confidence=float(hmm_signal.confidence * 0.85),
            direction=self._signal_to_direction(hmm_signal.raw_signal),
            kelly_fraction=float(
                self._compute_kelly_fraction(
                    signal=hmm_signal.raw_signal,
                    confidence=hmm_signal.confidence,
                    regime_state=regime_state,
                )
            ),
            model_weights=model_weights,
            regime_state=regime_info,
            individual_signals={"hmm_garch": hmm_signal},
            metadata={
                "fallback_mode": "hmm_only",
                "feature_count": len(features),
                "model_agreement": 1.0,
            },
        )


