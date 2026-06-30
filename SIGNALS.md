# NeuroQuant Signal Engine Documentation

This document describes the rules, filters, and mathematical checks executed by the `SignalEngine` (`backend/app/services/signal_engine.py`) before routing research signals to the execution or alert pipelines.

## Rule 1: Calibrated Confidence Threshold
- **Condition**: Ensemble confidence ($C$) must be $\ge 65\%$.
- **Rationale**: Any directional suggestion with low agreement among models is treated as neutral/noise and discarded.

## Rule 2: Regime Compatibility
- **Condition**: 
  - `BUY` / `STRONG_BUY` signals are **blocked** if HMM regime is `BEAR` or `CRISIS`.
  - `SELL` / `STRONG_SELL` signals are **blocked` if HMM regime is `BULL`.
- **Rationale**: Directional trades must align with the broader macro regime (detected via HMM-GARCH model) to avoid buying during structural drawdowns.

## Rule 3: Cost-Adjusted Sharpe (Risk/Reward Verification)
- **Condition**: Expected gain ($|\text{Target Price} - \text{Current Price}|$) must exceed 3 times the estimated round-trip transaction costs computed via `cost_model.py`:
  $$\text{Expected Reward} \ge 3 \times (\text{Brokerage} + \text{STT} + \text{Impact Cost})$$
- **Rationale**: Protects the account from churning on high-frequency setups where commission/slippage eats up all nominal profits.

## Database Integration
All approved signals are saved in PostgreSQL under the `EnsembleSignal` model with:
1. `inputs_used`: JSON snapshot of subscore signals (technical, pattern, momentum, xgboost, sentiment).
2. `outcome`: Realized outcome tracking status (e.g. `PENDING`, `WIN`, `LOSS`).
