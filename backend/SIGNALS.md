# NeuroQuant Signals Fusion Rule

The NeuroQuant system produces a single actionable prediction by combining multiple models and heuristics into a unified directional signal. This is governed by the Explicit Fusion Rule, implemented in the prediction engine.

## The Fusion Formula

```
Final Ensemble = Classical Composite ⊕ ML Probability ⊕ Regime Gate ⊕ Sentiment Tilt
```

### Components and Weights

#### 1. Classical Composite (40% Weight)
- Source: `TechnicalSignalEngine`
- Description: Evaluates price action, candlestick structures (e.g. Doji, Engulfing), support/resistance proximity, and standard momentum indicators (RSI, MACD crossover).
- Range: `[-1.0, 1.0]`

#### 2. ML Probability (60% Weight)
- Source: `XGBoostDirectionalClassifier`
- Description: Real-time probability of the asset moving upward (or downward) in the designated forecast window, transformed into a continuous scalar.
- Range: `[-1.0, 1.0]`

#### 3. Sentiment Tilt (Additive Boost)
- Source: `NewsSentiment` (FinBERT Engine)
- Description: Market and asset-specific news sentiment is evaluated. A net positive sentiment tilts the final ensemble upward, while negative sentiment tilts it downward.
- Range: Additive shift up to `±0.2` on the final ensemble scalar.

#### 4. Regime Gate (Veto Layer)
- Source: `HMM-GARCH Engine` (Hidden Markov Model)
- Description: Acts as an absolute veto layer to protect capital during unfavorable structural market conditions.
- Rules:
  - **BULL Regime**: Hard-blocks any SELL signals (Ensemble drops to 0.0 neutral).
  - **BEAR or CRISIS Regime**: Hard-blocks any BUY signals (Ensemble drops to 0.0 neutral).
  - **SIDEWAYS Regime**: Standard operations (no hard blocks).

---

## Output Signals

The final ensemble scalar dictates the directional signal and trading posture:

| Ensemble Scalar | Signal         | Action                        |
|-----------------|----------------|-------------------------------|
| `> 0.35`        | `STRONG_BUY`   | Aggressive entry / Kelly size |
| `0.15 to 0.35`  | `BUY`          | Standard entry                |
| `-0.15 to 0.15` | `NEUTRAL`      | Cash position / Hold          |
| `-0.35 to -0.15`| `SELL`         | Standard short                |
| `< -0.35`       | `STRONG_SELL`  | Aggressive short / Kelly size |

*Note: Position sizing is dynamically determined using a Kelly-fraction criterion scaled by the ensemble confidence and the GARCH conditional volatility forecast.*
