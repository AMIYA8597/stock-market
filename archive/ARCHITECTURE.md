# QuantEdge Architecture

## Overview
QuantEdge is a full-stack, local-first ML-driven educational paper-trading platform. The system ingests market data, computes technical and machine-learning features, runs statistical and deep learning models to predict directional movement, and exposes these insights through a fast API to a Next.js frontend.

## Components

### 1. Frontend (Next.js App Router)
- **Framework**: Next.js 14, React 18, Tailwind CSS, TypeScript.
- **State & Data**: React Query for API fetching and caching, Zustand for local state.
- **Charts**: Lightweight Charts (TradingView) for performant financial visualization (rendering candlesticks, expected move cones, and algorithmic signals).
- **Surfaces**: Terminal interface for day-trading, Research portal for model interpretability (SHAP waterfalls, Regime timelines), and Model Monitor for drift/accuracy tracking.

### 2. Backend (FastAPI / Python)
- **Framework**: FastAPI (async).
- **Database**: PostgreSQL (via SQLAlchemy 2.0 ORM and Alembic for migrations).
- **Background Tasks**: Celery with Redis as the broker/backend. Used for heavy tasks like ML training, daily data ingestion, and HMM/GARCH fitting.
- **Cache**: Redis for rapid API responses and rate limiting.

### 3. ML Pipeline
- **Data Ingestion**: Fetches raw OHLCV.
- **Feature Engineering**: Calculates technical indicators (TA-Lib / Pandas TA), calendar features, and embeds FinBERT sentiment. Features are strictly **causality-safe**, computed dynamically to ensure no look-ahead bias leaks into the training pipeline.
- **Models**:
  - **Volatility**: GARCH(1,1) for conditional volatility and expected-move cones.
  - **Regime**: 3-State Gaussian HMM (Bull, Bear, Sideways) to gate signal aggressiveness.
  - **Direction Classifiers**: XGBoost and LightGBM models trained via expanding-window **walk-forward cross-validation** (not randomized k-fold) to preserve chronological boundaries.
  - **Deep Learning**: LSTM/TFT sequence models for temporal patterns.
- **Explainability**: SHAP values are extracted post-inference for feature attribution (numerically additive and directly verifiable).
- **Governance**: Models are constantly evaluated for drift (PSI/KS metrics) and retrained autonomously if they degrade. Walk-forward metrics are persisted to the database to ensure absolute honesty in reported accuracy (no random shuffling or future leakage).
- **The Honesty Law Guard**: The training pipeline contains a strict structural blockade: if a model exceeds **75% directional accuracy** during walk-forward validation (which is practically impossible in efficient markets without data leakage), it triggers a `LeakageError` and is violently aborted before it can be deployed to the live serving database.

## Data Flow (Prediction End-to-End)
1. **Ingest**: End-of-day or intraday OHLCV is fetched.
2. **Features**: 40+ cross-sectional and temporal features are computed.
3. **Regime & Volatility**: GARCH and HMM are updated to tag the current environment.
4. **Inference**: The best-performing trained artifact (XGBoost/LightGBM) is loaded via `PredictionEngine`.
5. **Fusion**: ML probability + classical signals + regime gate are combined to produce a final `STRONG_BUY` to `STRONG_SELL` signal.
6. **Delivery**: The `/api/v1/predictions/latest/{symbol}` endpoint serves the JSON payload to the frontend.
7. **UI**: The React components render the probability gauge, SHAP waterfall, and the GARCH cone directly on the price chart.
