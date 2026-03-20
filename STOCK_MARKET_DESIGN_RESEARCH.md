# RESEARCH-BACKED STOCK MARKET APPLICATION DESIGN
## Professional Architecture for Advanced Algorithmic Trading Platform

**Based on:** Bloomberg Terminal, TradingView, Interactive Brokers, QuantConnect
**Standard:** M.Tech Thesis - IEEE/Springer Publication Ready
**Date:** March 2026

---

## SECTION 1: WHY CURRENT STATE IS BROKEN

### Problems in Current Architecture

```
❌ CURRENT STATE: 62 files, 0 integration
├── Backend: API endpoints return MOCK data (no DB calls)
├── Frontend: Components exist but wired to MOCK API (no real HTTP)
├── ML Models: Code complete but UNTRAINED (no checkpoints)
├── Database: Schema defined but NEVER TESTED (docker never run)
├── Features: Pipeline exists but NEVER COMPUTED (feature_vectors empty)
├── WebSocket: Infrastructure exists but NOT CONNECTED to data
└── Result: NOTHING WORKS TOGETHER — Theatre of code with no substance

⚠️ ROOT CAUSE: "Implement everything separately" mentality
   = 95% code written, 5% integration = 0% working platform
```

### What Production Platforms Look Like

**Bloomberg Terminal (1984-2024):**
- Data → Processing → Model → Display **all linked in real-time**
- Every UI element is connected to live data feed
- 300,000+ simultaneous connected terminals
- <100ms latency from data event to screen update

**TradingView:**
- Real-time OHLCV feed → WebSocket → Chart → Indicator calculation → Signal
- ALL async, ALL concurrent, ZERO blocking
- Charts update as price ticks arrive (not polling)

**Critical Insight:** Professional platforms are **data-driven**. Everything flows from SOURCE DATA through PROCESSING to DISPLAY. No disconnects.

---

## SECTION 2: PROPER ARCHITECTURE (CORRECT WAY)

### Architecture Principle: END-TO-END DATA FLOW

```
SOURCE DATA (Real-time)
    ↓
[Yfinance, NSE API, FRED, CoinGecko, Alpha Vantage]
    ↓
MESSAGE BUS (Redis Pub/Sub)
    ↓
[Price Tick Broadcaster] ← Subscribed by:
    ├─→ Database Layer (persist to OHLCv table)
    ├─→ Feature Computer (80+ factors in real-time)
    ├─→ ML Models (parallel inference pipeline)
    ├─→ WebSocket Router (broadcast to connected clients)
    └─→ Signal Combiner (ensemble weighted aggregation)
    ↓
PROCESSED SIGNALS + REGIME + PREDICTIONS
    ↓
[Redis Cache] ← Served by:
    ├─→ REST API Endpoints (fetch on-demand)
    ├─→ WebSocket Push (when updated)
    └─→ Dashboard Components (React renders live)
    ↓
USER INTERFACE (Terminal, Charts, Tables)
    ↓
USER ACTIONS (BUY/SELL, Backtest, Optimizer)
    ↓
[Portfolio Executor] + [Backtest Engine]
```

**Key Principle:** Once data enters at SOURCE, it flows through ALL systems automatically. No manual API calls. No polling. **Push-based, event-driven architecture.**

---

## SECTION 3: PROFESSIONAL UI/UX DESIGN

### Bloomberg Terminal — The Gold Standard for Trading UX

**Why Bloomberg Dominates Trading UI:**

1. **Information Density** — Maximum actionable data in minimum space
   - 3-column layout: sidebar | main work area | details panel
   - No wasted space, no unnecessary animations
   - Every pixel serves function

2. **Real-Time Responsiveness** — Price ticks appear instantly
   - Sub-100ms screen update when data arrives
   - No loading spinners (data is already there)
   - Numbers flash briefly when changed (user attention)

3. **Accessibility** — Designed for 8hr daily usage
   - Dark theme reduces eye strain
   - Large hover targets (42px minimum)
   - Clear visual hierarchy: critical data larger, supporting smaller

4. **Technical Precision** — Built for professionals who know exactly what they want
   - Keyboard shortcuts for power users
   - Customizable layouts (not for beginners, but experts need control)
   - Precise price display: decimals match instrument (2 for equity, 5 for crypto)

### Our Terminal Design (Implementing Above Principles)

```
┌─────────────────────────────────────────────────────────────────┐
│ 📊 NeuroquantTerminal | 09:30 AM | 🟢 BULL (P100=0.92) | ⚡    │  ← TopBar
├──────────────┬──────────────────────────────┬──────────────────┤
│              │                              │                  │
│  WATCHLIST   │   CANDLESTICK CHART         │  SIGNAL PANEL   │
│  ────────    │   ────────────────          │  ────────────   │
│              │                              │                  │
│ 🟢 RELIANCE  │  [High-quality chart with   │  DIR: 🔼 BUY     │
│  ₹2415.30    │  - Regime bands colored     │  CONF: 96%       │
│  +1.28%      │  - TFT attention overlay    │  KELLY: 8.2%     │
│  ↑ BUY 98%   │  - Volume profile          │                  │
│              │  - 8 indicator tabs]       │  WEIGHTS:        │
│ 🟢 TCS       │                             │  TFT:    32%     │
│  ₹3680.50    │  Indicators:               │  GARCH:  28%     │
│  +0.94%      │  RSI | MACD | Stoch...    │  GNN:    18%     │
│  ↑ BUY 89%   │                             │  LSTM:   15%     │
│              │  1m  5m  15m  1h  1d       │  XGB:     7%     │
│ 🟡 INFY      │                             │  ────────────    │
│  ₹2198.75    │  15:30 Signals:            │                  │
│  -0.32%      │  Order Flow | ML Time-S.  │  NEWS (3):       │
│  ↔ NEUTRAL   │                             │  • RELIANCE ...  │
│              │                             │  • Budget prep...│
│              │                             │                  │
│ 🟠 BAJAJ     │                             │                  │
│  AUTO        │                             │                  │
│              └──────────────────────────────┴──────────────────┘
│
│              ┌─ Right-click menu ─┐
│              │ Add to watchlist   │
│              │ Set alert          │
│              │ Open full page     │
│              └────────────────────┘
```

### Design System (CSS Architecture)

```typescript
// Global Color Tokens — EVERY color is a variable, never hardcoded hex

:root {
  // Base surfaces
  --bg-base:        #07090F;     // Darkest: app canvas
  --bg-surface:     #0C1018;     // Cards, panels
  --bg-elevated:    #111926;     // Hover, selected
  --bg-overlay:     #1A2333;     // Dropdowns, modals

  // Borders
  --border-subtle:  rgba(255, 255, 255, 0.06);
  --border-muted:   rgba(255, 255, 255, 0.12);
  --border-strong:  rgba(255, 255, 255, 0.22);

  // Text
  --text-primary:   #E8EDF5;     // Labels, prices
  --text-secondary: #8B97A8;     // Supporting text
  --text-muted:     #4A5568;     // Disabled, hints

  // Signals
  --signal-buy:     #00E676;     // Green: BUY, profit, positive
  --signal-sell:    #FF3B5C;     // Red: SELL, loss, negative
  --signal-neutral: #FFB800;     // Amber: NEUTRAL, warning
  --signal-bull:    rgba(0, 230, 118, 0.15);   // Green background
  --signal-bear:    rgba(255, 59, 92, 0.15);   // Red background
  --signal-sideways: rgba(255, 184, 0, 0.12);  // Amber background

  // Accents
  --accent-primary: #00D4F5;     // Cyan: interactive, focus
  --accent-secondary: #8B5CF6;   // Purple: ML models, special
  --accent-success: #00E676;     // Green: success state
  --accent-danger:  #FF3B5C;     // Red: destructive, error
  --accent-warning: #FFB800;     // Amber: caution

  // Fonts (loaded from @next/font)
  --font-mono:      'Berkeley Mono', monospace;     // Prices, code, numbers
  --font-display:   'Cabinet Grotesk', sans-serif;  // Headings, bold
  --font-body:      'Instrument Sans', sans-serif;  // Body text

  // Sizes
  --size-xs: 2px;
  --size-sm: 4px;
  --size-md: 8px;
  --size-lg: 16px;
  --size-xl: 24px;
  --size-2xl: 32px;
  --size-3xl: 48px;

  // Spacing (8px grid)
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;

  // Border radius
  --radius-sm:  4px;
  --radius-md:  6px;
  --radius-lg:  12px;
}

// Never use: colors outside variables, magic numbers, hardcoded hex values
// Usage example:
.price-badge {
  background: var(--bg-surface);
  color: var(--text-primary);
  border: 1px solid var(--border-muted);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  font-family: var(--font-mono);
  font-size: 14px;
}

.buy-signal {
  color: var(--signal-buy);
  font-weight: 600;
}

.sell-signal {
  color: var(--signal-sell);
  font-weight: 600;
}
```

---

## SECTION 4: BACKEND STRUCTURE (CORRECT ORGANIZATION)

### Layer 1: Data Ingestion (SOURCE)
```python
# Single responsibility: Fetch data from APIs
backend/
├── services/data_ingestion/
│   ├── base.py              # AsyncDataSource ABC
│   ├── yfinance_source.py   # Yahoo Finance adapter
│   ├── nse_source.py        # NSE India adapter
│   ├── coingecko_source.py  # Crypto source
│   ├── fred_source.py       # Macro data (Fed)
│   ├── alpha_vantage_source.py  # US intraday
│   └── orchestrator.py      # Async runner: fetch all sources concurrently
│
│   Data Flow:
│   orchestrator.py runs continuously:
│     → fetch_market_data()  [every 1 second for 1m interval]
│     → Store to Redis queue
│     → Emit to Redis pub/sub channel: "price_ticks"
```

### Layer 2: Stream Processing (PROCESS)
```python
backend/
├── services/stream_processor/
│   ├── price_tick_consumer.py  # Listen to Redis pub/sub "price_ticks"
│   ├── feature_computer.py     # Compute 80+ factors on new OHLCV
│   ├── model_inference.py      # Run ML models on new features
│   ├── signal_combiner.py      # Aggregate model outputs
│   └── cache_updater.py        # Store results to Redis cache
│
│   Flow: price_tick → features → models → signals → cache
│
│   CRITICAL: All async coroutines, no blocking calls
│   target latency: source → cache: <100ms
```

### Layer 3: Storage (PERSIST)
```python
backend/
├── database/
│   ├── models/          # SQLAlchemy ORM
│   │   ├── ohlcv.py         # TimescaleDB hypertable
│   │   ├── feature_vector.py
│   │   ├── ml_prediction.py
│   │   └── signal.py
│   │
│   └── connection.py    # Async engine, session factory
│
│   Write pattern:
│     ✓ Stream processor writes to ohlcv continuously
│     ✓ Features computed, stored to feature_vectors
│     ✓ Predictions stored to ml_predictions
│     ✓ Signals stored to ensemble_signals
```

### Layer 4: API (SERVE)
```python
backend/
├── api/v1/
│   ├── market.py        # GET /market/quote/{symbol}
│   │                    # Gets data from cache + DB, no computation
│   ├── signals.py       # GET /signals/{symbol}
│   ├── regime.py        # GET /regime/current
│   ├── explain.py       # GET /explain/shap/{symbol}
│   ├── backtest.py      # POST /backtest/run (async jobs)
│   └── portfolio.py     # POST /portfolio/optimize
│
│   Pattern:
│     request → check Redis cache (1s TTL) → return cached OR
│               query DB → return latest → update cache
│
│   NEVER compute on request. Always pre-computed and cached.
```

### Layer 5: WebSocket (PUSH)
```python
backend/
├── websocket/
│   ├── connection_manager.py  # Room subscriptions
│   ├── price_broadcaster.py   # Listen Redis → send to clients
│   ├── signal_broadcaster.py  # Listen signal updates → send
│   └── router.py              # /ws/prices, /ws/signals, /ws/alerts
│
│   Pattern:
│     ✓ Client connects to /ws/prices
│     ✓ Server subscribes to Redis channel "price_ticks"
│     ✓ When price tick arrives in Redis, broadcast to all connected clients
│     ✓ Clients receive update <50ms after source data
```

### Result: Professional Backend Architecture

```
Real-time Data Source (1-second ticks)
            ↓
    [Redis Pub/Sub: "price_ticks"]
            ↓
Stream Processors (feature + model + signal pipeline)
            ↓
    [Redis Cache: session data, signals, regime]
            ↓
    [PostgreSQL: TimescaleDB, permanent storage]
            ↓
REST API (GET endpoints) + WebSocket (push updates)
            ↓
Frontend Dashboard (React components)
```

---

## SECTION 5: FRONTEND STRUCTURE (CORRECT ORGANIZATION)

### Component Hierarchy (Clear Separation of Concerns)

```
apps/web/src/
├── app/                          # Next.js App Router pages
│   ├── layout.tsx               # Root layout: providers, themes
│   ├── page.tsx                 # Redirect to /terminal
│   ├── (dashboard)/
│   │   ├── layout.tsx           # Dashboard wrapper with sidebar
│   │   ├── terminal/
│   │   │   ├── page.tsx         # Terminal main page
│   │   │   └── layout.tsx       # Terminal 3-column layout
│   │   ├── markets/
│   │   │   ├── page.tsx         # Market overview
│   │   │   └── stocks/
│   │   │       ├── page.tsx     # Stock table browser
│   │   │       └── [symbol]/
│   │   │           └── page.tsx # Full stock detail page
│   │   ├── research/
│   │   │   ├── page.tsx         # Research hub
│   │   │   ├── regime-analysis/page.tsx
│   │   │   └── explainability/[symbol]/page.tsx
│   │   ├── backtest-lab/
│   │   │   ├── page.tsx         # Strategy configurator
│   │   │   └── results/[jobId]/page.tsx
│   │   ├── portfolio/
│   │   │   ├── page.tsx         # Holdings overview
│   │   │   └── optimizer/page.tsx
│   │   └── model-monitor/page.tsx
│   │
│   └── (auth)/
│       ├── login/page.tsx
│       └── register/page.tsx
│
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx          # Left navigation sidebar
│   │   ├── TopBar.tsx           # Header bar: logo, search, account
│   │   └── Footer.tsx           # Optional footer info
│   │
│   ├── terminal/                # Terminal-specific components
│   │   ├── TerminalLayout.tsx   # 3-column grid layout
│   │   ├── Watchlist/
│   │   │   ├── index.tsx        # Scrollable asset list
│   │   │   ├── WatchlistRow.tsx # Single row
│   │   │   └── useWatchlistWS.ts # WebSocket hook
│   │   ├── ChartSection/
│   │   │   ├── index.tsx
│   │   │   ├── CandlestickChart.tsx
│   │   │   ├── IndicatorPanel.tsx
│   │   │   └── VolumeChart.tsx
│   │   └── SignalPanel/
│   │       ├── index.tsx        # Right panel
│   │       ├── SignalCard.tsx
│   │       └── EnsembleWeightPie.tsx
│   │
│   ├── charts/
│   │   ├── CandlestickChart/
│   │   │   ├── index.tsx        # TradingView wrapper
│   │   │   ├── useChartSetup.ts # Setup & teardown
│   │   │   ├── IndicatorPlugin.ts  # EMA, BB, VWAP
│   │   │   ├── RegimeBands.tsx  # Colored state backgrounds
│   │   │   └── SignalMarkers.tsx # Buy/sell arrows
│   │   │
│   │   ├── RegimeChart/
│   │   ├── ShapWaterfall/
│   │   ├── EfficientFrontier/
│   │   └── MonteCarloFan/
│   │
│   ├── tables/
│   │   ├── StockTable.tsx       # Sortable stock list
│   │   ├── TradeLog.tsx         # Back test trades
│   │   └── HoldingsTable.tsx    # Portfolio holdings
│   │
│   └── ui/
│       ├── Button.tsx           # Base button component
│       ├── Card.tsx             # Card wrapper
│       ├── Badge.tsx            # Signal badges
│       ├── Tooltip.tsx          # Hover tooltips
│       └── Skeleton.tsx         # Loading placeholder
│
├── hooks/
│   ├── useWebSocket.ts          # Reconnect logic
│   ├── usePriceFeed.ts          # Subscribe to /ws/prices
│   ├── useSignalFeed.ts         # Subscribe to /ws/signals
│   ├── useRegime.ts             # Current regime state
│   └── useBacktest.ts           # Poll backtest status
│
├── lib/
│   ├── api.ts                   # Typed fetch wrapper
│   ├── wsManager.ts             # WebSocket singleton (one per app)
│   ├── chartUtils.ts            # OHLCV normalization
│   └── numberFormat.ts          # Price, % formatting
│
├── store/
│   ├── terminalStore.ts         # Zustand: selected symbol, timeframe
│   ├── portfolioStore.ts        # Holdings, P&L
│   └── alertStore.ts            # Active alerts
│
├── types/
│   ├── market.ts                # Price, OHLCV, Quote types
│   ├── signal.ts                # Signal, Model, Ensemble types
│   └── api.ts                   # API response schemas
│
├── styles/
│   ├── globals.css              # CSS variables, resets
│   ├── terminal.css             # Terminal layout
│   └── charts.css               # Chart-specific styles
│
└── env.local                    # Example: NEXT_PUBLIC_API_URL
```

### Component Design Pattern (Correct Way)

```typescript
// ✅ GOOD: Clear separation, reusable, testable

// 1. Pure presentation component
interface PriceCardProps {
  price: number;
  change: number;        // percentage
  changePct: number;     // e.g., +1.28
}

export function PriceCard({ price, change, changePct }: PriceCardProps) {
  const style = change >= 0 ? 'text-green-500' : 'text-red-500';
  return (
    <div className="price-card">
      <span className="price">${price.toFixed(2)}</span>
      <span className={style}>{change >= 0 ? '↑' : '↓'} {changePct}%</span>
    </div>
  );
}

// 2. Data-fetching hook (separate concern)
export function usePriceQuote(symbol: string) {
  const [quote, setQuote] = useState<Quote | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Subscribe to WebSocket
    const unsubscribe = websocket.subscribe(`prices:${symbol}`, (data) => {
      setQuote(data);
    });
    return unsubscribe;
  }, [symbol]);

  return { quote, loading };
}

// 3. Container component (connects hooks to UI)
export function WatchlistRow({ symbol }: { symbol: string }) {
  const { quote, loading } = usePriceQuote(symbol);
  const { signal } = useSignalFeed(symbol);

  if (loading) return <Skeleton />;

  return (
    <div className="watchlist-row">
      <span className="ticker">{symbol}</span>
      <PriceCard
        price={quote.price}
        change={quote.change}
        changePct={quote.changePct}
      />
      <SignalBadge direction={signal.direction} confidence={signal.confidence} />
    </div>
  );
}

// ❌ BAD: Everything mixed together, impossible to test

export function BadWatchlistRow({ symbol }: { symbol: string }) {
  const [price, setPrice] = useState(0);
  const [displayedPrice, setDisplayedPrice] = useState(0);

  // Mixing data-fetch logic with UI rendering
  useEffect(() => {
    fetch(`/api/v1/market/quote/${symbol}`)
      .then(r => r.json())
      .then(data => {
        setPrice(data.price);
        // Business logic computation in UI component
        setDisplayedPrice(
          Math.round((data.price + data.change) * 100) / 100
        );
      });
  }, [symbol]);

  return (
    <div>
      <span>{displayedPrice.toString()}</span>
      {/* Hardcoded colors instead of CSS variables */}
      {price > displayedPrice ? (
        <span style={{ color: '#00E676' }}>↑</span>
      ) : (
        <span style={{ color: '#FF3B5C' }}>↓</span>
      )}
    </div>
  );
}
```

---

## SECTION 6: ML/AI STRUCTURE (CORRECT ORGANIZATION)

### ML Pipeline: Clean Separation

```
backend/research/

1. DATA LAYER (inputs)
   ├── feature_engineering/
   │   ├── price_factors.py      # Momentum, drawdown
   │   ├── volatility_factors.py # Vol, GARCH, realized
   │   ├── microstructure.py     # OFI, spread
   │   ├── calendar_effects.py   # Day-of-week, season
   │   ├── sentiment_factors.py  # News sentiment
   │   └── pipeline.py           # Sequential execution, no look-ahead

2. MODEL LAYER (algorithms)
   ├── models/
   │   ├── tft/
   │   │   ├── architecture.py   # TFT class with all components
   │   │   ├── components.py     # GRN, VSN, GLU modules
   │   │   ├── trainer.py        # Training loop
   │   │   └── inference.py      # Forward pass, return predictions
   │   ├── hmm_garch/
   │   ├── gnn/
   │   ├── lstm_attention/
   │   ├── xgboost_model/
   │   └── ensemble/

3. EVALUATION LAYER (validation)
   ├── backtesting/
   │   ├── engine.py             # Vectorized simulation
   │   ├── walk_forward.py       # CPCV cross-validation
   │   ├── monte_carlo.py        # 10k path bootstrap
   │   └── analytics.py          # Sharpe, Sortino, drawdown, all metrics
   │
   ├── risk/
   │   ├── var_models.py         # VaR, CVaR calculation
   │   └── stress_testing.py     # 2008, COVID scenarios
   │
   └── explainability/
       ├── shap_explainer.py     # Feature attribution
       └── attention_extractor.py # Visualize model reasoning

4. OPTIMIZATION LAYER (portfolio)
   ├── portfolio/
   │   ├── mean_variance.py      # MVO with Ledoit-Wolf
   │   ├── black_litterman.py    # BL with ML views
   │   ├── hrp.py                # Hierarchical Risk Parity
   │   └── cvar_optimization.py  # CVaR constraints
```

### Training Pipeline (Not Mixed with Inference)

```python
# backend/pipelines/training_pipeline.py

# CORRECT WAY: Separate training from serving

async def train_hmm_garch_pipeline():
    """Training runs offline, NOT on serving machine."""
    # 1. Fetch historical OHLCV
    ohlcv = await fetch_5_years_data(symbols=['NIFTY', 'SENSEX', ...])
    
    # 2. Compute returns
    returns = compute_log_returns(ohlcv)
    
    # 3. Train HMM with Baum-Welch EM
    model = HMM_GARCH(n_states=4, max_iterations=500)
    model.fit(returns)
    
    # 4. Save checkpoint
    torch.save(model.state_dict(), '/app/data/models/hmm_garch.pt')
    
    # 5. Update version in Redis
    redis.set('model_version:hmm_garch', '2026_03_20_v1')

async def train_tft_pipeline():
    """Train on GPU (expensive), save checkpoint, deploy to serving."""
    features = await fetch_feature_vectors(days=1260)  # 5 years
    dataset = TimeSeriesDataset(features, seq_len=60, horizon=21)
    dataloader = DataLoader(dataset, batch_size=64, shuffle=True)
    
    model = TemporalFusionTransformer(...)
    optimizer = AdamW(model.parameters())
    
    for epoch in range(50):
        loss = training_loop(model, optimizer, dataloader)
        # Checkpoint periodically
        if epoch % 10 == 0:
            torch.save(model.state_dict(), f'/app/data/models/tft_epoch_{epoch}.pt')
    
    torch.save(model.state_dict(), '/app/data/models/tft_final.pt')

# SERVING: Never train on serving machine
# Just load checkpoint and run inference

async def inference_pipeline(symbol: str, features: array) -> float:
    """Ultra-fast on serving machine."""
    if not model_cache.has('tft'):
        model = TemporalFusionTransformer(...)
        model.load_state_dict(torch.load('/app/data/models/tft_final.pt'))
        model_cache.set('tft', model)
    
    model = model_cache.get('tft')
    with torch.no_grad():
        prediction = model(features)
    return prediction  # <50ms
```

---

## SECTION 7: IMPLEMENTATION ROADMAP (CORRECT SEQUENCE)

### Phase 0: FOUNDATION (Critical First Step)
```
Step 1: Database Verification  
   docker-compose up timescaledb redis
   alembic upgrade head
   Verify: \dt in psql shows 10 tables
   
Step 2: Seed Real Data
   Fetch 5 years daily OHLCV for 40 symbols
   Verify: ohlcv table has ~1260 rows per symbol
   
Step 3: Compute Features
   Run feature pipeline: 80+ factors
   Verify: feature_vectors table populated, no NaN
```

**Without these 3 steps, nothing works. Current state tried to skip them.**

### Phase 1: BACKEND DATA PIPELINE
```
Step 4: Data Ingestion Service
   Implement all adapters (yfinance, NSE, etc.)
   Stream processor: read price → publish Redis → compute features
   
Step 5: Database Persistence
   Stream processor writes to TimescaleDB
   Cache layer: Redis with 1s TTL
   
Step 6: WebSocket Broadcasting
   Redis pub/sub → WebSocket clients
   Test: two browser tabs receive price ticks
```

### Phase 2: ML MODELS
```
Step 7: Train HMM-GARCH
   Baum-Welch EM on NIFTY 5y returns
   Save checkpoint
   
Step 8: Train TFT
   Temporal Fusion Transformer on features
   Quantile outputs (P10/P50/P90)
   Save checkpoint
   
Step 9: Train GNN + Ensemble
   Graph neural network + ensemble orchestrator
   Parallel inference pipeline
```

### Phase 3: API ENDPOINTS
```
Step 10: REST API (GET endpoints)
   /market/quote, /signals, /regime, etc.
   All GET endpoints serve from cache (no computation)
   
Step 11: Backtest + Optimizer
   Vectorized backtesting engine
   Portfolio optimizers (MVO, BL, HRP, CVaR)
```

### Phase 4: FRONTEND
```
Step 12: Wire Frontend to Real API
   Update api.ts: real HTTP calls instead of mocks
   Connect hooks to WebSocket
   
Step 13: Build Pages
   Terminal → Markets → Research → Backtest → Portfolio
   Each page fully responsive and functional
```

---

## SECTION 8: QUALITY METRICS

### What Professional Platform Looks Like

| Metric | Target | Current |
|--------|--------|---------|
| API Response Time | <150ms P95 | ❌ Mock data (∞) |
| WebSocket Latency | <50ms | ❌ Not connected |
| Model Inference | <100ms | ❌ Not trained |
| UI Responsiveness | 60fps | ❌ Not tested |
| Code Test Coverage | 80%+ | ❌ ~10% |
| Type Safety (TS) | strict: true | ❌ Many any's |
| DB Query Time | <50ms | ❌ Never tested |
| Feature Freshness | < 1 second | ❌ Never computed |

### Deployment Readiness Checklist

```
❌ Database tested end-to-end
❌ Real data flowing through system
❌ Features computed automatically
❌ ML models trained and saved
❌ API endpoints returning real data
❌ WebSocket live updating
❌ Frontend wired to real API
❌ Performance benchmarked
❌ Error handling tested
❌ Security reviewed
❌ Documentation complete
```

Current state: 0/11 items done. That's why it's "begger" (broken).

---

## SECTION 9: NEXT IMMEDIATE ACTION

### DO THIS FIRST (before writing any more code):

```bash
# 1. Start database
docker-compose up timescaledb redis

# 2. Run migrations
cd backend && alembic upgrade head

# 3. Verify schema
psql postgresql://postgres:PASSWORD@localhost:5432/algo_trading
\dt  -- Should show 10 tables

# 4. Seed historical data
python -m backend.scripts.seed_historical_data  # 5y OHLCV

# 5. Check data is there
SELECT COUNT(*) FROM ohlcv;  -- Should be ~50k rows

# 6. Compute features
python -m backend.pipelines.data_pipeline --features-only

# 7. Check features
SELECT COUNT(*) FROM feature_vectors;  -- Should be ~50k

# 8. THEN start ML training
python -m backend.research.models.hmm_garch.trainer
python -m backend.research.models.tft.trainer
```

**CURRENT STATE ERROR:** Tried to build frontend before database even existed.
**CORRECT STATE:** Data → Storage → Processing → API → UI (in that order)

---

## CONCLUSION: PROFESSIONAL vs BEGGAR ARCHITECTURE

### Why Current = "Beggar"
- 62 files that don't talk to each other
- Mock data everywhere (no real data flow)
- Beautiful code that does nothing
- Like building a Ferrari engine, transmission, wheels separately without bolting them together

### Why New Approach = Professional
- Vertical slice: Data → Process → Store → Serve → Display (end-to-end)
- Every component has clear input/output
- Real data flowing through entire system
- Like building integrated Ferrari: wheels, transmission, engine bolted together and running

---

**Start with STEP 1: Database verification. Everything else depends on working data pipeline.**
