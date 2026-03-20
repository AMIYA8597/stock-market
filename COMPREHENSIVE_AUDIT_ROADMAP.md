# 📋 COMPREHENSIVE AUDIT + SEQUENTIAL IMPLEMENTATION ROADMAP
**Status**: March 20, 2026 | Scope: Complete NEUROQUANT Platform (new-prompt.txt v1)

---

## PART 1: COMPLETE CURRENT STATE AUDIT

### ✅ CURRENTLY IMPLEMENTED (62 files, ~15k LOC backend)

#### Database Layer
- [x] TimescaleDB schema sketched (ohlcv, feature_vectors, regime_states, ml_predictions, ensemble_signals, portfolio_holdings, transactions, alerts, backtest_jobs, news_sentiment)
- [x] Alembic structure exists (migrations/0001_*, 0002_*)
- [x] SQLAlchemy ORM models defined (10+ model files)

#### Backend API Infrastructure
- [x] FastAPI app bootstrap (app/main.py with CORS, lifespan)
- [x] API routers defined with stub endpoints:
  - market.py: quote, history, indices, movers, heatmap, search, economic-calendar (7 endpoints)
  - signals.py: signal, bulk, history (3 endpoints)
  - regime.py: current, history, statistics (3 endpoints)
  - backtest.py: run, status, results (3 endpoints)
  - portfolio.py: holdings, transaction, performance, risk-metrics, optimize (5 endpoints)
  - screener.py: run, presets (2 endpoints)
  - alerts.py, monitor.py, explainability.py
- [x] Response schema classes defined (QuoteResponse, SignalResponse, RegimeResponse, etc.)
- [x] WebSocket infrastructure sketched (connection_manager, price_broadcaster, signal_broadcaster)

#### Data Ingestion Layer
- [x] All 5 async data sources: yfinance_source, nse_source, coingecko_source, fred_source, alpha_vantage_source
- [x] Orchestrator with concurrent fetch + retry logic + database persistence
- [x] Support for: 1m/5m/15m/1h/1d intervals, NSE/NYSE/CRYPTO/INDEX/ETF assets

#### ML Models - COMPLETE IMPLEMENTATIONS
- [x] **HMM-GARCH**: StudentTHMM with Baum-Welch EM, Viterbi, 4-state regime, per-state GARCH(1,1)
- [x] **TFT**: Full architecture - GRN, VSN, LSTM encoder-decoder, 8-head attention, quantile loss
- [x] **GNN**: GLASSO graph builder, GAT+GRU temporal layers, spillover risk computation
- [x] **LSTM-Attention**: Bi-LSTM + multi-head attention
- [x] **XGBoost**: Rolling retraining pipeline with SHAP feature selector
- [x] **Ensemble**: Orchestrator, dynamic weight manager (regime × rolling Sharpe), signal combiner, Kelly sizer

#### Research Modules - COMPLETE
- [x] **Feature Engineering**: 80+ factors across 8 categories (price, vol, microstructure, calendar, etc.)
- [x] **Backtesting**: Vectorized engine, CPCV walk-forward, Monte Carlo bootstrap, comprehensive analytics
- [x] **Portfolio**: MVO+Ledoit-Wolf, Black-Litterman, HRP (López de Prado), CVaR optimization
- [x] **Risk**: VaR models, stress testing, FF5 attribution, tail risk EVT
- [x] **Explainability**: SHAP, attention extraction, counterfactual generation
- [x] **Statistical tests**: DM test, deflated Sharpe, MinBTL, Diebold-Mariano

#### Pipelines & Orchestration
- [x] data_pipeline.py: Concurrent ingestion for 40 symbols
- [x] training_pipeline.py: End-to-end HMM-GARCH training
- [x] inference_pipeline.py: Ensemble aggregation
- [x] retraining_trigger.py: ADWIN drift detection → Celery task dispatch

#### Frontend - PARTIALLY IMPLEMENTED
- [x] Terminal page exists (3-column Bloomberg layout)
- [x] TopBar component (regime pill, P&L display, signal status)
- [x] Watchlist component (dual mobile/desktop view)
- [x] ChartSection (SVG sparkline + Recharts)
- [x] Global CSS design system (20+ color tokens, all typography)
- [x] Type definitions (market.ts, models.ts, api.ts)

---

## PART 2: CRITICAL GAPS (What's Missing for "Done")

### 🔴 MAJOR BLOCKERS (Prevents Tests from Running)

#### Database
- [ ] **Alembic migrations NOT runnable**: init.sql exists but needs comprehensive seed data + constraints
- [ ] **No database connection test**: Cannot verify schema creation end-to-end
- [ ] **Redis integration incomplete**: Not configured in docker-compose.yml fully

#### Backend API
- [ ] **NO endpoint implementations**: All routers have stub responses only
  - market.quote: returns mock data (not real yfinance call)
  - signals: no actual inference pipeline call
  - backtest: no job queue integration
  - portfolio.optimize: no cvxpy solver call
- [ ] **Real WebSocket broadcasting NOT connected**: price_broadcaster exists but no Redis pub/sub wiring
- [ ] **Database reads/writes NOT implemented**: Endpoints don't query TimescaleDB
- [ ] **No inference pipeline callable**: Models exist but not wired into request handlers

#### ML Models
- [ ] **Models exist but NOT callable**: 
  - TFT checkpoint loading not implemented
  - HMM-GARCH inference entry point missing
  - GNN embedding computation not exposed
  - Ensemble.orchestrator() exists but errors on missing model weights
- [ ] **Feature vectors NOT computed**: Pipeline.py exists but never called on real data
- [ ] **Model training scripts NOT runnable**: No entry points for `python -m research.models.tft.trainer`

#### Frontend
- [ ] **API client stub**: contracts-api.ts returns mock data (no actual HTTP calls)
- [ ] **WebSocket client NOT connected**: useWebSocket hook exists but ws://localhost:8000/ws unreachable
- [ ] **NO real data flows**: Terminal shows mock prices, not live data
- [ ] **Recharts charts render empty**: ChartSection loads but getData() not wired
- [ ] **Pages incomplete**:
  - /markets/stocks page exists but empty
  - /research, /backtest-lab, /portfolio/optimizer pages missing
  - /markets/stocks/[symbol] detail page stubbed only

#### Testing & Validation
- [ ] **Zero test files**: No test_*.py for ML modules
- [ ] **No integration tests**: Cannot verify API → DB → Model pipeline
- [ ] **No E2E tests**: Playwright skipped in CI

---

## PART 3: SEQUENCED IMPLEMENTATION (12-STEP CRITICAL PATH)

### PHASE 1: DATABASE + DATA FOUNDATIONS (Days 1-3)

**STEP 1: Database Initialization**
- [ ] Verify docker-compose.yml has timescaledb+redis services
- [ ] Run: `docker-compose up timescaledb redis`
- [ ] Run: `alembic upgrade head` (executes init.sql + create tables)
- [ ] Test: Connect via psql → verify all 10 tables created with correct schema
- [ ] Test: Check continuous aggregates created for ohlcv_1h
- [ ] Commit: "infrastructure: initialize TimescaleDB and Redis with full schema"

**STEP 2: Seed Initial Data**
- [ ] Create script: `scripts/seed_historical_data.py`
  - Fetch 5y daily OHLCV for: 25 NSE stocks (RELIANCE, TCS, INFY, HDFC, ITC, HUL, WIPRO, BAJAJ-AUTO, LT, MARUTI, AXISBANK, ICICIBANK, HDFC-BANK, SUNPHARMA, ASIANPAINT, BRITANNIA, HDFCBANK, INDIGO, LUPIN, NESTLEIND, POWERGRID, TITAN, ULTRACEMCO, DRREDDY, HINDALCO)
  - Fetch 5y daily for: 10 US stocks (MSFT, AAPL, GOOGL, NVDA, TSLA, JNJ, JPM, PG, KO, BA)
  - Fetch 5y daily for: 5 crypto (BTC-USD, ETH-USD, BNB-USD, XRP-USD, SOL-USD)
  - Fetch indices: ^NSEI, ^BSESN, ^GSPC, ^IXIC, ^DJI, ^VIX
- [ ] Persist to TimescaleDB ohlcv table
- [ ] Verify: 5y × 252 trading days = ~1260 bars per asset
- [ ] Commit: "data: seed 5-year historical OHLCV for 40 symbols"

**STEP 3: Feature Compute Pipeline**
- [ ] Run: `python -m backend.research.feature_engineering.pipeline --symbols RELIANCE.NS,TCS.NS --date-from 2019-01-01 --date-to 2024-12-31`
- [ ] Verify: feature_vectors table populated with 80+ float columns
- [ ] Check: No NaN values after 60-day warmup
- [ ] Commit: "pipeline: compute all 80+ feature factors for feature_vectors hypertable"

---

### PHASE 2: BACKEND API CORE (Days 4-6)

**STEP 4: Market Data API (Real Implementation)**
- [ ] Implement `backend/app/api/v1/market.py`:
  ```python
  @router.get("/quote/{symbol}")
  async def get_quote(symbol: str):
      # 1. Check Redis cache (TTL 1s)
      # 2. Query TimescaleDB: latest ohlcv bar
      # 3. Compute: change, change_pct from prev close
      # 4. Fetch regime via HMM current state
      # 5. Fetch latest signal from ensemble_signals table
      # 6. Return QuoteResponse with all fields populated
  
  @router.get("/history/{symbol}")
  async def get_history(symbol: str, interval: str, period: str):
      # Query continuous aggregate ohlcv_1h or raw ohlcv from TimescaleDB
      # Return list of OHLCVBar with proper time ordering
  ```
- [ ] Test: `curl http://localhost:8000/api/v1/market/quote/RELIANCE.NS` → returns real price
- [ ] Commit: "api: implement /market/quote and /market/history endpoints with real data"

**STEP 5: HMM-GARCH Training + Regime Endpoint**
- [ ] Run trainer: `python -m backend.research.models.hmm_garch.trainer --data-path data/processed/nifty_5y.csv --save-to data/models/hmm_garch.pkl`
  - Trains on ^NSEI 5y daily returns
  - Saves: transition matrix A, mean/vol per state, GARCH params
- [ ] Implement regime current state query:
  ```python
  @router.get("/regime/current")
  async def get_regime_current():
      # Load HMM model from checkpoint
      # Get latest NIFTY price from TimescaleDB
      # Compute Viterbi state
      # Compute per-state GARCH conditional vol
      # Return RegimeCurrentResponse
  ```
- [ ] Test: `/regime/current` returns valid state ∈ {0,1,2,3}
- [ ] Commit: "models: train HMM-GARCH on ^NSEI, implement /regime/current endpoint"

**STEP 6: TFT Model Training + Inference**
- [ ] Run trainer: `python -m backend.research.models.tft.trainer --data-path data/processed/features --save-to data/models/tft.pt`
  - Trains on all 25 NSE stocks + 10 US stocks simultaneously
  - Multi-asset, multi-horizon (1d, 5d, 21d)
  - Saves PyTorch checkpoint
- [ ] Implement inference wrapper:
  ```python
  async def tft_predict(symbol: str, features: np.ndarray) -> TFTPrediction:
      model = torch.load("data/models/tft.pt")
      with torch.no_grad():
          p10, p50, p90 = model.forward(features)
      return TFTPrediction(p10=p10, p50=p50, p90=p90)
  ```
- [ ] Test: inference < 50ms per asset
- [ ] Commit: "models: train TFT on multi-asset dataset, add inference pipeline"

---

### PHASE 3: ENSEMBLE + REAL-TIME SIGNALS (Days 7-8)

**STEP 7: Ensemble Orchestrator**
- [ ] Complete `backend/research/models/ensemble/orchestrator.py`:
  - Load all 5 models (HMM, TFT, GNN, LSTM, XGBoost) in parallel
  - For given symbol+features: run inference on all models
  - Collect raw signals: `[s_hmm, s_tft, s_gnn, s_lstm, s_xgb]`
  - Return structured output with all model predictions
- [ ] Test: end-to-end inference < 100ms
- [ ] Commit: "models: implement ensemble orchestrator with parallel model inference"

**STEP 8: Signal Generation API**
- [ ] Implement `/signals/{symbol}` endpoint:
  ```python
  @router.get("/signals/{symbol}")
  async def get_signal(symbol: str):
      # 1. Fetch latest features from feature_vectors table
      # 2. Call ensemble.orchestrator(symbol, features)
      # 3. Weight models via weight_manager (regime × rolling Sharpe)
      # 4. Combine signals via signal_combiner
      # 5. Compute Kelly fraction sizing
      # 6. Store in ensemble_signals table
      # 7. Return SignalResponse with all details
  ```
- [ ] Add `/signals/bulk` for 50 symbols in parallel
- [ ] Test: `/signals/RELIANCE.NS` returns valid ensemble signal
- [ ] Commit: "api: implement /signals endpoints with full ensemble inference"

---

### PHASE 4: PORTFOLIO + BACKTEST ENGINES (Days 9-10)

**STEP 9: Portfolio Optimization**
- [ ] Implement `POST /portfolio/optimize` endpoint:
  ```python
  @router.post("/portfolio/optimize")
  async def optimize_portfolio(request: OptimizeRequest):
      # Parse method: hrp | black_litterman | cvar | mean_variance
      # Fetch covariance matrix from feature_vectors (rolling 252d)
      # If use_ml_views=true: get ensemble signals as BL views
      # Run optimizer (cvxpy-based)
      # Return weights, efficient frontier (100 points), metrics
  ```
- [ ] All 4 optimizers must work: HRP, BL, MVO (Ledoit-Wolf), CVaR
- [ ] Test: weights sum to 1, constraints satisfied, Sharpe > 1.0
- [ ] Commit: "optimization: implement all four portfolio optimizers with ML signal views"

**STEP 10: Backtesting API**
- [ ] Implement `POST /backtest/run` → async job submission:
  ```python
  @router.post("/backtest/run")
  async def run_backtest(config: BacktestConfig):
      job_id = uuid()
      # Queue async backtest task to Celery
      # Return job_id immediately, status=PENDING
      # Frontend polls /backtest/status/{job_id}
  
  # Background worker processes:
  # 1. Fetch OHLCV for universe over date range
  # 2. Compute signals via ensemble for each day
  # 3. Run vectorized backtest engine
  # 4. Run CPCV walk-forward if enabled
  # 5. Run Monte Carlo if enabled
  # 6. Compute all statistics (Sharpe, Sortino, Calmar, etc.)
  # 7. Store results in backtest_jobs table
  ```
- [ ] Implement `GET /backtest/results/{job_id}` to fetch full results
- [ ] Commit: "backtest: implement async backtesting with CPCV walk-forward and Monte Carlo"

---

### PHASE 5: FRONTEND DATA FLOWS (Days 11-12)

**STEP 11: Real API Integration**
- [ ] Update `apps/web/src/lib/contracts-api.ts`:
  ```typescript
  export async function getQuote(symbol: string): Promise<QuoteResponse> {
      return fetch(`${API_URL}/market/quote/${symbol}`).then(r => r.json());
  }
  
  export async function getHistory(symbol: string, interval: string, period: string) {
      return fetch(`${API_URL}/market/history/${symbol}?interval=${interval}&period=${period}`)
          .then(r => r.json());
  }
  
  export async function getSignal(symbol: string): Promise<SignalResponse> {
      return fetch(`${API_URL}/signals/${symbol}`).then(r => r.json());
  }
  
  export async function getRegimeCurrent() {
      return fetch(`${API_URL}/regime/current`).then(r => r.json());
  }
  ```
- [ ] Update Terminal components to call real endpoints
- [ ] Test: Terminal loads RELIANCE.NS with real price, signal, regime
- [ ] Commit: "frontend: wire Terminal to real backend API endpoints"

**STEP 12: WebSocket Real-Time Updates**
- [ ] Implement Redis Pub/Sub broadcaster:
  ```python
  # In data ingestion pipeline:
  # Every 1s: publish latest tick to redis.publish('prices', {symbol, price, change})
  
  @router.websocket("/ws/prices")
  async def websocket_prices(ws: WebSocket):
      await manager.connect(ws, "prices")
      redis_client = redis.Redis()
      pubsub = redis_client.pubsub()
      pubsub.subscribe('prices')
      
      while True:
          msg = pubsub.get_message()
          if msg:
              await ws.send_json(msg)
  ```
- [ ] Similar for `/ws/signals` (triggered on new inference)
- [ ] Test: Two browser tabs → both receive price ticks within 1s
- [ ] Commit: "websocket: implement real-time price + signal broadcasts via Redis pub/sub"

---

## PART 4: FRONTEND PAGES IMPLEMENTATION (Sequential Order)

**Priority 1 (Must Have for MVP)**
- [ ] `/terminal` → Complete (Top priority - is the main page)
- [ ] `/markets/stocks` → Implement (asset table with signals)
- [ ] `/markets/stocks/[symbol]` → Implement (detail page with full charts)
- [ ] `/research/regime-analysis` → Implement (HMM regime visualization)

**Priority 2 (High Value)**
- [ ] `/backtest-lab` → Implement (strategy backtester UI)
- [ ] `/portfolio/optimizer` → Implement (portfolio optimization UI)
- [ ] `/research/explainability/[symbol]` → Implement (SHAP + attention)

**Priority 3 (Nice to Have)**
- [ ] `/research/correlation-graph` → D3 force-directed graph
- [ ] `/model-monitor` → Model accuracy dashboard
- [ ] `/screener` → Stock screener UI

Each page must:
- Use real API endpoints (not mocks)
- Support all responsive breakpoints (mobile/tablet/desktop)
- Show loading states + error boundaries
- Use design system colors (CSS variables)
- Animate with Lucide icons

---

## PART 5: TESTING & VALIDATION CHECKLIST

### Unit Tests (Add test_*.py for each module)
- [ ] test_tft.py: Forward pass shape, quantile loss computation
- [ ] test_hmm_garch.py: EM convergence, Viterbi correctness
- [ ] test_gnn.py: GLASSO adjacency, GAT attention
- [ ] test_ensemble.py: Weight sum to 1, signal ∈ [-1,+1]
- [ ] test_backtest.py: Known return sequence → verified Sharpe
- [ ] test_features.py: No NaN, no look-ahead bias, shape (T, 80)

### Integration Tests
- [ ] API → DB: quote endpoint queries TimescaleDB, returns real price
- [ ] Model → API: signal endpoint loads model, runs inference, returns response
- [ ] DB → Frontend: fetch quote, display in Terminal

### E2E Tests (Playwright)
- [ ] Terminal loads with RELIANCE.NS at current price
- [ ] Click symbol in watchlist → chart updates
- [ ] WebSocket receives price tick update
- [ ] /markets/stocks table shows 50 assets with signals
- [ ] /backtest-lab runs strategy, shows equity curve

---

## PART 6: SUCCESS METRICS (User Requirements Met)

✅ **All Responsive**: Every page works mobile (320px) → tablet (768px) → desktop (1440px)
✅ **All Dynamic Real Data**: Prices from yfinance, signals from ensemble, regime from HMM
✅ **Best Design**: Bloomberg 3-column terminal, proper color scheme, animations
✅ **Zero Skipping**: All endpoints implemented, all pages functional, all tests passing

---

## NEXT IMMEDIATE ACTION

**Start with STEP 1: Database Initialization**

```bash
# Terminal 1: Start database services
docker-compose up timescaledb redis --build

# Terminal 2: Run migrations
cd backend
alembic upgrade head

# Terminal 3: Seed historical data
python scripts/seed_historical_data.py --full-history

# Terminal 4: Start backend API
uvicorn app.main:app --reload --port 8000

# Terminal 5: Start frontend
cd apps/web
pnpm dev

# Open browser: http://localhost:3000/terminal
```

Expected: Terminal loads with real RELIANCE.NS price, shows current regime, displays ensemble signal.
