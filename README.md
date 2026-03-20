════════════════════════════════════════════════════════════════════════════════
ALGORITHMIC TRADING INTELLIGENCE PLATFORM
M.Tech Thesis — NIT Rourkela 2026
Research-Publishable | Institutional-Grade | Production-Ready
════════════════════════════════════════════════════════════════════════════════

## Project Architecture

This is a research-grade **monorepo** for an algorithmic trading platform featuring:
- **Frontend**: Next.js 14 (App Router, TypeScript strict)
- **Backend**: FastAPI async (Python 3.12, PostgreSQL + TimescaleDB)
- **ML Systems**: 5 ensemble models (TFT, HMM-GARCH, GNN, LSTM-Attn, XGBoost)
- **Infrastructure**: Docker Compose (PostgreSQL, Redis, Celery, Prometheus, Grafana)

## Directory Structure

```
algo-trading-thesis/
├── frontend/                           # Next.js 14 UI (apps/web in monorepo)
│   ├── src/app/                       # Routes: terminal, markets, research, backtest, portfolio
│   ├── src/components/                # Charts, terminal, research, portfolio UIs
│   ├── src/hooks/                     # WebSocket, data fetching, state
│   └── public/favicon.svg
│
├── backend/                            # FastAPI monolith (Python 3.12)
│   ├── app/
│   │   ├── main.py                    # FastAPI app factory, lifespan, CORS
│   │   ├── api/v1/                    # All REST endpoints (/market, /signals, /backtest, etc)
│   │   ├── websocket/                 # Real-time: /ws/prices, /ws/signals, /ws/alerts
│   │   ├── core/                      # Config, security (JWT), DB, logging
│   │   ├── models/                    # SQLAlchemy ORM (User, Symbol, OHLCV, ML Predictions)
│   │   ├── schemas/                   # Pydantic v2 request/response models
│   │   ├── database/                  # Async SQLAlchemy, Redis, Alembic migrations
│   │   └── services/                  # Business logic (data ingestion, signals, portfolio)
│   │
│   ├── research/                       # CORE THESIS — All ML algorithms
│   │   ├── models/                    # 7 model implementations:
│   │   │   ├── tft/                   # Temporal Fusion Transformer (quantile forecasting)
│   │   │   ├── hmm_garch/             # HMM with state-dependent GARCH (regime detection)
│   │   │   ├── gnn/                   # Graph Neural Network (systemic risk)
│   │   │   ├── lstm_attention/        # LSTM + multi-head attention
│   │   │   ├── xgboost_model/         # XGBoost baseline with SHAP
│   │   │   ├── ensemble/              # Weight aggregation + Kelly sizing
│   │   │   └── online_learner/        # Drift detection (ADWIN) + EWC fine-tuning
│   │   ├── feature_engineering/       # 80+ factors: price, volatility, microstructure, FF5
│   │   ├── backtesting/               # Vectorized engine, walk-forward, Monte Carlo, analytics
│   │   ├── portfolio/                 # MVO, Black-Litterman, HRP, CVaR optimization
│   │   ├── risk/                      # VaR, CVaR, stress testing, tail risk metrics
│   │   ├── explainability/            # SHAP, attention extraction, counterfactuals
│   │   └── notebooks/                 # Jupyter: EDA, training, validation, results
│   │
│   ├── pipelines/                      # Orchestration (data → features → inference → training)
│   ├── tasks/                          # Celery tasks (backtest, retrain, ingestion)
│   ├── tests/                          # Unit, integration, property-based tests
│   ├── pyproject.toml                  # ruff, mypy, pytest config (strict)
│   └── requirements.txt
│
├── infrastructure/
│   ├── docker-compose.yml              # PostgreSQL, Redis, Celery, Flower, Prometheus, Grafana
│   ├── docker-compose.prod.yml         # Production overrides
│   ├── postgres/init.sql               # TimescaleDB setup, hypertables
│   ├── nginx/nginx.conf
│   ├── prometheus/prometheus.yml
│   └── monitoring/                     # Grafana dashboards
│
├── data/
│   ├── raw/                            # API dump cache (git-ignored)
│   ├── processed/                      # Feature matrices
│   ├── models/                         # Trained checkpoints (.pt, .pkl, .joblib)
│   └── results/                        # Backtest artifacts, JSON metrics
│
├── packages/                           # Shared monorepo packages
│   ├── config/                         # Tailwind, TypeScript config
│   ├── types/                          # Shared TS types for UI + docs
│   └── ui/                             # Base UI components
│
├── scripts/                            # One-off utility scripts
├── .github/workflows/                  # CI/CD: lint, test, deploy, retrain
├── Makefile                            # Build targets: dev, test, lint, train, backtest, docs
├── .env.example                        # All required environment variables (documented)
├── docker-compose.yml                  # Local dev stack
└── pyproject.toml                      # Root workspace config
```

## Quick Start (Local Development)

### Frontend Only
```bash
pnpm install
pnpm --filter @neuroquant/web dev
# Open http://localhost:3000
```

### Backend Only
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### Full Stack (Docker Compose)
```bash
docker compose up --build
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/api/v1
# WebSocket: ws://localhost:8000/ws
# Flower (Celery): http://localhost:5555
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3001 (admin/admin)
```

## Build Order (Execute Strictly)

1. **Scaffold** - All directories, __init__.py, config files
2. **Database** - TimescaleDB schema, Alembic migrations
3. **Data Ingestion** - All data sources (yfinance, CoinGecko, FRED, NSE)
4. **Features** - 80+ factor computation pipeline
5. **FastAPI** - Auth, quote endpoint, WebSocket infrastructure
6. **HMM-GARCH** - Regime detection training
7. **TFT** - Temporal Fusion Transformer training
8. **GNN** - Graph Neural Network training
9. **Ensemble** - Weight aggregation + Kelly
10. **Backtesting** - CPCV walk-forward engine
11. **Portfolio** - All optimizer implementations
12. **Explainability** - SHAP, attention, counterfactuals
13. **API Endpoints** - Complete all remaining endpoints
14. **Frontend** - All pages and components (terminal, markets, research, backtest, portfolio)
15. **Validation** - Notebooks, tests, statistical tests

## Command Reference

```bash
# Development
make dev                 # docker compose up --build

# Code Quality
make lint               # ruff check + mypy + eslint
make test               # pytest backend/ + jest frontend/
make format             # ruff format + prettier

# Data & Models
make data-fetch         # 5y daily OHLCV for universe
make features           # Compute all 80+ factors
make train-all          # HMM → GNN → TFT → ensemble calibration
make backtest           # Full CPCV backtest ensemble strategy

# Research
make notebooks          # jupyter lab backend/notebooks/
make docs               # Generate OpenAPI + README

# Deployment
make build-prod         # docker compose -f docker-compose.prod.yml build
make deploy-staging     # Push to staging via GitHub Actions
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14, React 19, TypeScript 5.x, TradingView Charts, D3, Three.js, Recharts |
| **Backend** | FastAPI (async), Python 3.12, SQLAlchemy, Pydantic v2 |
| **Database** | PostgreSQL 16 + TimescaleDB (time-series hypertables) |
| **Cache** | Redis 7 (pub/sub, session, rate-limit) |
| **Task Queue** | Celery (async training, backtesting, data ingestion) |
| **ML** | PyTorch, scikit-learn, XGBoost, scipy, statsmodels, cvxpy |
| **Monitoring** | Prometheus, Grafana, Structlog (JSON logging) |
| **Testing** | pytest, hypothesis (property-based), pytest-asyncio, jest, React Testing Library |
| **CI/CD** | GitHub Actions (lint, test, deploy, model retrain schedule) |

## Code Quality Standards (Non-Negotiable)

- **Python**: Python 3.12, strict mypy, ruff (all rules), Google-style docstrings with math/citations
- **TypeScript**: strict mode, no `any`, Zod runtime validation, Suspense + Error Boundaries
- **Commits**: Conventional commits (feat/fix/perf/test/docs), semantic versioning
- **Tests**: All core algorithms tested (shape, numerical correctness, edge cases, no look-ahead bias)
- **Docstrings**: Include algorithm formula (LaTeX), paper reference, args, returns, raises

## Research Deliverables

All notebooks runnable end-to-end with publication-quality figures:

1. **01_EDA_and_stationarity.ipynb** - ADF, KPSS, return distributions, ACF/PACF
2. **03_hmm_regime_detection.ipynb** - Viterbi decoding, regime statistics, vol forecast validation
3. **04_tft_training_and_eval.ipynb** - Training curves, Directionality Markup test vs ARIMA, Winkler score
4. **06_ensemble_walk_forward.ipynb** - CPCV fold Sharpes, deflated Sharpe calculation, benchmark comparison
5. **07_portfolio_optimization.ipynb** - Efficient frontier, HRP dendrogram, constraint satisfaction
6. **09_statistical_significance.ipynb** - DM test, MCS, multiple testing correction, min backtest length

## Key Features

✅ **Multi-Horizon Forecasting** - TFT quantile predictions (P10/P50/P90) for 1/5/21-day horizons
✅ **Regime Detection** - HMM-GARCH with 4 market states + conditional volatility forecasts
✅ **Systemic Risk** - GNN detecting spillover risk via GLASSO sparse graphs
✅ **Explainability** - SHAP + attention weights + counterfactuals for every prediction
✅ **Portfolio Optimization** - HRP, MVO+LW, Black-Litterman, CVaR via cvxpy
✅ **Robust Backtesting** - CPCV, walk-forward, Monte Carlo, statistical significance tests
✅ **Real-Time Terminal** - Bloomberg-style UI with live prices, signals, regime state
✅ **WebSocket Feeds** - Subscriptions for prices, signals, alerts, backtest progress
✅ **Drift Detection** - ADWIN concept drift + online learning via EWC
✅ **Production Infrastructure** - Docker Compose, health checks, structured logging, monitoring

## Deployment

### Local Development (No Docker)
```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
python scripts/data_pipeline.py --full-history
uvicorn app.main:app --reload
```

### Production (Docker)
```bash
docker compose -f docker-compose.prod.yml up -d
# Automatic CI/CD via GitHub Actions on merge to main
```

## Testing & Validation

```bash
# Run all backend tests with coverage
pytest backend/tests/ -v --cov=backend/app --cov=backend/research

# Property-based tests (Hypothesis)
pytest backend/tests/property_tests/ -v

# Type checking
mypy backend/app backend/research --strict

# Lint
ruff check backend/

# Run notebooks (validate thesis evidence)
cd backend && jupyter nbconvert --to notebook --execute notebooks/*.ipynb
```

## Contributing

1. Create feature branch from `develop`
2. Make commits following [conventional commits](https://www.conventionalcommits.org/)
3. Run `make lint` + `make test` before pushing
4. Open PR against `develop` (auto CI triggers)
5. After merge to `develop`, manual PR to `main` (triggers deployment)

## M.Tech Thesis References

Algorithms implemented per academic standards with reproducible results:

- **TFT**: Lim et al. (2021). NeurIPS. Temporal Fusion Transformers for Interpretable Multi-horizon TS Forecasting.
- **HMM-GARCH**: Hamilton (1989, 1994). Regime-switching models. Bollerslev (1986). GARCH models.
- **GNN**: Kipf & Welling (2016). Graph Convolutional Networks. GAT: Veličković et al. (2017).
- **HRP**: López de Prado (2016). Machine Learning for Asset Managers. Hierarchical clustering.
- **SHAP**: Lundberg & Lee (2017). A Unified Approach to Interpreting Model Predictions.
- **Walk-Forward CPCV**: de Prado et al. (2018). Advances in Financial Machine Learning. Combinatorial purged cross-validation.

## License

This project is confidential and for M.Tech thesis submission to NIT Rourkela only.

════════════════════════════════════════════════════════════════════════════════
