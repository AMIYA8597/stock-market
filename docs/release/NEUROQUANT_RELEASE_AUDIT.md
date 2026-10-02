# NeuroQuant Release Audit Report

**Date**: 2026-10-02
**Auditor**: Automated forensic audit
**Platform**: NeuroQuant AI Stock Market Intelligence

---

## 1. Data Integrity

| Source | Status | Notes |
|--------|--------|-------|
| yfinance | ACTIVE | Primary fallback for all market data |
| Upstox Analytics | CONFIGURED | Token set, instrument sync endpoint ready, aliases not yet populated |
| Supabase PostgreSQL | CONNECTED | Empty — no instruments, no OHLCV, no quotes ingested |
| Redis | FALLBACK | localhost:6379 unavailable on Cloud Run → InMemoryCache used |

**Verdict**: All live market data comes from yfinance. Upstox integration wired but requires instrument sync. No fabricated prices.

---

## 2. Model Honesty Audit

| Model | Label | Actual Implementation | Status | Artifact |
|-------|-------|----------------------|--------|----------|
| XGBoost | XGBoost | Real XGBClassifier + isotonic calibration | UNTRAINED | No .pkl on disk |
| LSTM-Attention | LSTM-Attention | Real PyTorch LSTM + attention | UNTRAINED | No .pkl on disk |
| HMM-GARCH | HMM-GARCH | From-scratch Student-t HMM + GARCH(1,1) | TRAINED | hmm_garch/reliance.ns_hmm_garch.json |
| TFT | QuantileLGBM | **NOT TFT** — LightGBM quantile regression | UNTRAINED | No .pkl on disk |
| GNN | ContagionRiskAnalyzer | **NOT GNN** — formula-based heuristic | HEURISTIC | N/A |
| Online Learner | Online Learner | Incremental logistic regression | UNTRAINED | No .pkl on disk |
| LSTM Forecaster | LSTM Forecaster | Trains from scratch each call (15 epochs) | EPHEMERAL | N/A |
| Meta-Learner | Meta-Learner | Logistic regression on OOF predictions | UNTRAINED | No .pkl on disk |
| FinBERT | FinBERT | ProsusAI/finbert (falls back to VADER) | PRETRAINED | HuggingFace download |

**Violations found and fixed**:
- TFT label was misleading → added `actual_model: "QuantileLGBM"` disclosure
- GNN was labeled `trained` → changed to `heuristic` with disclosure
- Forecast method now tracked per prediction (`lstm_scratch`/`exponential_smoothing`/`flat_projection`)

**Remaining**: 6 of 9 models are UNTRAINED. Training pipeline exists (`backend/research/`) with Purged Walk-Forward CV but has never been run to produce persistent artifacts.

---

## 3. Chart Mode Audit

### Implemented (real data from OHLCV) — 30 modes
Candlestick, Hollow Candlestick, OHLC Bar, Line, Area, Baseline, Volume, Heikin-Ashi, Renko, Kagi, Point & Figure, Range Bars, Three-Line Break, Equivolume, Tick, Volume Profile, Market Profile, Spread, Relative Strength, Mountain, VWAP, Anchored VWAP, CVD, Returns Distribution, Histogram Returns, Rolling Volatility, Drawdown, Rolling Sharpe, Rolling Beta, Fibonacci, Pivot Points, Ichimoku Cloud

### UNAVAILABLE (shown with watermark) — 12 modes
| Mode | Reason |
|------|--------|
| Open Interest | Requires real exchange OI data feed |
| OI + Price | Requires real exchange OI data feed |
| Put-Call Ratio | Requires real options chain data |
| IV Smile/Skew | Requires real options chain with IV per strike |
| IV Surface | Requires real options chain across strikes and expiries |
| Volatility Cone | Requires custom visualization (not time-series) |
| Correlation Heatmap | Requires multi-asset data loaded simultaneously |
| Rolling Correlation | Requires benchmark data loaded simultaneously |
| Elliott Wave | Requires specialized wave-detection algorithm |
| Gann | Requires specialized geometric projection engine |
| Order Book Depth | Requires real-time Level 2 order book data |
| Footprint Chart | Requires tick-level trade data |

**Violations found and fixed**:
- 6 modes (iv-smile, volatility-cone, correlation-heatmap, rolling-correlation, elliott-wave, gann) were silently rendering plain candlesticks → now show UNAVAILABLE watermark
- 3 modes (open-interest, oi-price, put-call-ratio) were manufacturing synthetic data from OHLCV → now show UNAVAILABLE watermark

---

## 4. Infrastructure Status

| Component | Status | Details |
|-----------|--------|---------|
| Backend | Cloud Run (asia-south1) | 2 CPU, 2Gi RAM, auto-scaling 0-4 |
| Frontend | Vercel | Auto-deploys from main branch |
| Database | Supabase PostgreSQL | Connected but empty (no ingested data) |
| Cache | InMemoryCache | Redis unavailable on Cloud Run, using in-process fallback |
| Auth | Supabase Auth | Configured |
| Secrets | .env committed to repo | **SECURITY RISK** — should use Cloud Run secrets |

---

## 5. API Endpoints Added

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/market/instruments/sync-upstox` | Trigger NSE instrument master sync |
| `GET /api/v1/market/instruments/status` | Check instrument/alias counts |
| `GET /api/v1/predictions/model-inventory` | Honest model training status |
| `GET /api/v1/health/system-audit` | Comprehensive system status |

---

## 6. Outstanding Items

1. **Run Upstox instrument sync** — call `/instruments/sync-upstox` once on Cloud Run
2. **Train ML models** — run training pipeline to produce .pkl artifacts
3. **Move secrets out of .env** — use Cloud Run secret manager
4. **Redis on Cloud Run** — consider Memorystore or accept InMemoryCache
5. **Real options data source** — needed for OI, PCR, IV charts
6. **Real order book feed** — needed for depth, footprint, order-flow charts
