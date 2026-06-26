# NEUROQUANT — PHASE-2 AUDIT REPORT

This report lists the fake, dead, and duplicate files found in the codebase during Step 1 of the NEUROQUANT Phase-2 upgrade.

## 1. Fake Models and Mock Logic

### `backend/app/services/ml_engine/orchestrator.py`
- **Status**: Fake / Dead
- **Description**: Claims to implement parallel inference from TFT, HMM-GARCH, GNN, LSTM-Attn, and XGBoost. In reality, it uses hand-coded linear formulas combined with a hash-of-string symbol seed jitter (`_symbol_seed` using `ord()`) to fake model output.
- **Dependency**: This file is never imported or used by any live route in the backend app.

### `backend/app/api/v1/explain.py` (Attention Logic)
- **Status**: Mock Logic
- **Description**: Line 176 onwards mocks multi-head attention weights for the TFT model by shifting the mean of the absolute log returns instead of using actual attention outputs from a neural network.

### `backend/app/api/v1/models.py`
- **Status**: Fake/Hardcoded Metrics
- **Description**: Returns completely hardcoded dummy metrics for model accuracy (e.g., `directional_accuracy=0.6400`), model drift (e.g., KS statistic and ADWIN p-values), and ensemble weights history.

---

## 2. Dead / Unused Modules

### `backend/app/services/prediction/`
- **Files**:
  - `arima_predictor.py`
  - `base.py`
  - `predictor_factory.py`
  - `prophet_predictor.py`
  - `random_forest_predictor.py`
- **Status**: Dead / Unused
- **Description**: These files define a predictor framework and factory that are completely unused. No endpoint or service imports from this subpackage.

### `backend/app/research/feature_engineering/price_volatility_stub.py`
- **Status**: Dead / Stub
- **Description**: Contains placeholder empty definitions for `PriceFactorsBuilder` and `VolatilityFactorsBuilder`. The real implementations are located in `backend/research/feature_engineering/`.

---

## 3. Duplicate / Placeholder Directories

### `research/` (at the root of the workspace)
- **Files**:
  - `research/models/hmm_garch/regime_detector.py` (Placeholder using a simple 20-day MA crossover)
  - `research/backtesting/walk_forward.py` (Placeholder returning `[0.5, 0.7, 0.9]`)
  - `research/backtesting/engine.py` (Placeholder simplified backtest)
  - `research/backtesting/analytics.py` (Placeholder analytics functions)
  - `research/backtesting/statistical_tests.py` (Placeholder stats tests)
- **Status**: Duplicate / Placeholders
- **Description**: This directory duplicates the name of the `backend/research` module but contains only simplified stubs. The real quant research code and models are in `backend/research/`.
