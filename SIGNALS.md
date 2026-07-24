# NeuroQuant Signal Engine Documentation

This document describes the rules, filters, and mathematical checks executed by the `SignalEngine` (`backend/app/services/ml_engine/prediction_engine.py` and `signal_engine.py`) before routing research signals to the execution or alert pipelines.

## Fusion Rule
The core prediction is a fused score combining classical technical analysis, machine learning outputs, sentiment, and market regime.

```python
# Exact Formula:
final = (0.4 * technical_score) + (0.6 * ML_score) + sentiment_tilt
```

- **Technical Score (`tech_score`)**: Composite of RSI, MACD, Bollinger Bands (-1.0 to 1.0).
- **ML Score (`ml_score`)**: Normalized probability from the trained XGBoost or LightGBM model (-1.0 to 1.0). If untrained, defaults to 0.
- **Sentiment Tilt (`sentiment_tilt`)**: Extracted from FinBERT (or simulated equivalent for missing news), scaled by 0.15.

## Regime Gate
The fused score is gated by the HMM-identified market regime:
- **Condition**: 
  - `BUY` / `STRONG_BUY` signals are **suppressed** (capped at 0.2, effectively NEUTRAL) if HMM regime is `BEAR` or `CRISIS`.
  - `SELL` / `STRONG_SELL` signals are **suppressed** (capped at -0.2) if HMM regime is `BULL`.
- **Rationale**: Directional trades must align with the broader macro regime (detected via HMM-GARCH model) to avoid buying during structural drawdowns.

## Confidence & Sizing Threshold
- **Confidence Extraction**: Confidence is $| \text{Probability}_{up} - 0.5 | \times 2$.
- **Condition**: Ensemble confidence ($C$) must be $\ge 65\%$ for `STRONG_` signals.
- **Sizing**: Position sizing is determined by the Kelly criterion, taking into account the `ensemble_confidence` and GARCH expected-move cone.

## Cost-Adjusted Sharpe (Risk/Reward Verification)
- **Condition**: Expected gain ($|\text{Target Price} - \text{Current Price}|$) must exceed 3 times the estimated round-trip transaction costs computed via `cost_model.py`:
  $$\text{Expected Reward} \ge 3 \times (\text{Brokerage} + \text{STT} + \text{Impact Cost})$$
- **Rationale**: Protects the account from churning on high-frequency setups where commission/slippage eats up all nominal profits.

## Database Integration
All approved signals are saved in PostgreSQL under the `EnsembleSignal` model with:
1. `inputs_used`: JSON snapshot of subscore signals (technical, pattern, momentum, xgboost, sentiment).
2. `outcome`: Realized outcome tracking status (e.g. `PENDING`, `WIN`, `LOSS`).
