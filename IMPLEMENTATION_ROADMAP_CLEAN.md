# CLEAN IMPLEMENTATION PLAN — STEP BY STEP
## Fix current "beggar" state → professional platform

---

## PHASE 1: FOUNDATION (Days 1-3)
### Focus: Get database and real data flowing

### STEP 1.1: Database Verification
```bash
# Start database + Redis
docker-compose up -d timescaledb redis

# Run migrations (test they work)
cd backend
alembic upgrade head

# Verify schema exists
psql postgresql://postgres:password@localhost:5432/algo_trading
\dt  # Should show 10 tables: users, symbols, ohlcv, feature_vectors, etc.
```

**Success Criteria:**
- ✅ 10 tables created with correct schema
- ✅ TimescaleDB extension active
- ✅ Continuous aggregate ohlcv_1h exists
- ✅ Can INSERT/SELECT from ohlcv table

### STEP 1.2: Seed Historical Data (5 years)
```bash
# Create new script: backend/scripts/seed_data.py
python backend/scripts/seed_data.py --symbols NIFTY,RELIANCE.NS,TCS.NS,INFY.NS,BAJAJFINSV.NS --periods 5y --interval 1d

# Verify data loaded
SELECT COUNT(*) FROM ohlcv;  # Should be ~1260 * 40 = ~50,400 rows
SELECT DISTINCT symbol_id FROM ohlcv;  # Should see 40 symbols
```

**Success Criteria:**
- ✅ 40 symbols × 1260 days = ~50,400 rows of OHLCV
- ✅ No NULL values in OHLCV columns
- ✅ Dates properly sorted ascending

### STEP 1.3: Feature Engineering Pipeline
```bash
# Run feature computation (once, completes in ~30 mins)
python -m backend.pipelines.data_pipeline --mode features-only

# Verify features exist
SELECT COUNT(*) FROM feature_vectors;  # ~50,400 rows
SELECT COUNT(DISTINCT symbol_id) FROM feature_vectors;  # 40 symbols
```

**Success Criteria:**
- ✅ feature_vectors populated with 80+ columns per row
- ✅ No NaN values after warmup period (first 60 rows per symbol OK)
- ✅ Features are comparable across symbols (normalized)

---

## PHASE 2: ML MODEL TRAINING (Days 4-6)
### Focus: Train all 5 models, save checkpoints

### STEP 2.1: Train HMM-GARCH Model
```bash
# Command
python -m backend.research.models.hmm_garch.trainer --data-source timescaledb --save-path /app/data/models/hmm_garch.pt

# Expected output
# Training HMM on 1260 days NIFTY returns
# Baum-Welch EM: iteration 1, logL=-2143.28
# Baum-Welch EM: iteration 2, logL=-2141.95
# ...
# Converged at iteration 47
# Model saved to /app/data/models/hmm_garch.pt
# GARCH fit for state 0: ω=0.00012, α=0.089, β=0.891
# GARCH fit for state 1: ω=0.00008, α=0.115, β=0.874
# ...

# Verify checkpoint
ls -lh /app/data/models/hmm_garch.pt  # Should be ~1MB
```

**Success Criteria:**
- ✅ Model converges (EM iterations < 500)
- ✅ Checkpoint saved (file exists)
- ✅ GARCH parameters sensible (α+β < 1)
- ✅ Regime probabilities sum to 1

### STEP 2.2: Train TFT Model
```bash
# Train on GPU if available (CPU will be slow but works)
python -m backend.research.models.tft.trainer --epochs 50 --batch-size 64 --use-gpu

# Expected output
# Loading features: 40 symbols × 1260 days → shape (40, 1260, 80)
# Creating TimeSeriesDataset: seq_len=60, horizon=21 → 1179 samples per symbol
# Epoch 1/50: loss=0.456, val_loss=0.521
# Epoch 2/50: loss=0.412, val_loss=0.487
# ...
# Epoch 50/50: loss=0.187, val_loss=0.223
# Model saved to /app/data/models/tft.pt
# P50 RMSE vs ARIMA: 0.034 vs 0.067 (DM test p=0.003)

# Verify
ls -lh /app/data/models/tft.pt  # Should be ~50MB (weights)
```

**Success Criteria:**
- ✅ Training converges (loss decreases)
- ✅ Validation loss < 0.25 (reasonable for returns prediction)
- ✅ Checkpoint saved
- ✅ P50 forecast RMSE better than ARIMA (DM test p < 0.05)

### STEP 2.3: Train GNN + Others
```bash
python -m backend.research.models.gnn.trainer --epochs 30
python -m backend.research.models.lstm_attention.trainer --epochs 40
python -m backend.research.models.xgboost_model.trainer --n-estimators 500

# All 3 should complete in ~2 hours on CPU
```

---

## PHASE 3: API LAYER (Days 7-8)
### Focus: Connect database to REST endpoints

### STEP 3.1: Implement Real GET Endpoints
```python
# backend/app/api/v1/market.py

@router.get("/market/quote/{symbol}")
async def get_quote(symbol: str, db: AsyncSession = Depends(get_db)):
    """Get current or latest quote from database."""
    
    # 1. Check Redis cache (TTL 1s)
    cached = await redis_client.get(f"quote:{symbol}")
    if cached:
        return json.loads(cached)
    
    # 2. If not cached, query database
    stmt = select(ohlcv).where(
        ohlcv.symbol == symbol
    ).order_by(ohlcv.time.desc()).limit(1)
    
    latest = await db.execute(stmt)
    result = latest.scalar_one_or_none()
    
    if not result:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    # 3. Transform to response schema
    response = {
        "ticker": symbol,
        "price": float(result.close),
        "change": float(result.close - result.open),
        "change_pct": ((result.close - result.open) / result.open) * 100,
        "volume": int(result.volume),
        "timestamp": result.time.isoformat()
    }
    
    # 4. Cache for 1 second
    await redis_client.setex(f"quote:{symbol}", 1, json.dumps(response))
    
    return response

# Similar for /market/history, /market/indices, etc.
```

**Success Criteria:**
- ✅ `curl http://localhost:8000/api/v1/market/quote/RELIANCE.NS` returns real data
- ✅ Response time <150ms
- ✅ Cache hits show sub-50ms responses
- ✅ Data matches database

### STEP 3.2: Implement Signal Endpoints
```python
# Load all trained models at startup
@app.on_event("startup")
async def load_models():
    app.state.tft_model = TemporalFusionTransformer(...)
    app.state.tft_model.load_state_dict(torch.load('/app/data/models/tft.pt'))
    
    app.state.hmm_garch_model = HMM_GARCH(...)
    app.state.hmm_garch_model.load_state_dict(torch.load('/app/data/models/hmm_garch.pt'))
    # ... load all 5 models

@router.get("/signals/{symbol}")
async def get_signals(symbol: str, db: AsyncSession = Depends(get_db)):
    """Get ML ensemble signal for symbol."""
    
    # 1. Fetch latest features from database
    features = await get_latest_features(symbol, db)  # 80-dim vector
    
    # 2. Run all models in parallel
    predictions = await asyncio.gather(
        run_tft_inference(app.state.tft_model, features),
        run_hmm_inference(app.state.hmm_garch_model, features),
        run_gnn_inference(app.state.gnn_model, symbol, features),
        run_lstm_inference(app.state.lstm_model, features),
        run_xgboost_inference(app.state.xgb_model, features)
    )
    
    # 3. Combine signals with ensemble weights
    signal = ensemble_combiner.combine(
        predictions,
        model_weights=get_dynamic_weights(),
        regime_state=get_regime_state()
    )
    
    return {
        "symbol": symbol,
        "signal": signal.value,  # ∈ [-1, +1]
        "direction": signal.direction,  # BUY/SELL/NEUTRAL
        "confidence": signal.confidence,  # 0-1
        "models": signal.model_details
    }
```

**Success Criteria:**
- ✅ `/signals/{symbol}` responds in <100ms
- ✅ Returns proper ensemble signal
- ✅ All 5 models contributing
- ✅ Signal makes market sense (BUY when bullish, SELL when bearish)

---

## PHASE 4: WEBSOCKET REAL-TIME (Days 9)
### Focus: Live price/signal updates

### STEP 4.1: Price Ticker Stream
```python
# backend/services/stream_processor.py

async def price_ticker_loop():
    """Continuously fetch prices, publish to WebSocket."""
    
    while True:
        try:
            # 1. Fetch latest tick for all monitored symbols
            prices = await fetch_latest_prices(['RELIANCE.NS', 'TCS.NS', ...])
            
            # 2. Publish each to Redis pub/sub
            for symbol, price_data in prices.items():
                await redis_client.publish(
                    f"price_tick:{symbol}",
                    json.dumps(price_data)
                )
            
            # 3. Store to database (async, doesn't block)
            asyncio.create_task(store_ohlcv(prices))
            
            # 4. Trigger feature compute
            asyncio.create_task(compute_features_for_symbols(prices.keys()))
            
            # 5. Trigger model inference
            asyncio.create_task(run_ensemble_inference_for_symbols(prices.keys()))
            
            # 6. Wait 1 second (intraday frequency)
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Price ticker error: {e}")
            await asyncio.sleep(5)  # Retry after 5s

# WebSocket endpoint
@router.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket):
    await websocket.accept()
    
    # Subscribe to Redis channel
    pubsub = redis_client.pubsub()
    
    try:
        while True:
            # 1. Wait for message on Redis
            message = await pubsub.get_message_async()
            
            # 2. Forward to WebSocket client
            if message:
                await websocket.send_json(json.loads(message['data']))
            
            await asyncio.sleep(0.01)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    
    finally:
        await websocket.close()
```

**Success Criteria:**
- ✅ `/ws/prices` receives tick updates every 1 second
- ✅ Multiple browser tabs both receive updates
- ✅ Latency: source → Redis → WebSocket → browser < 100ms total

---

## PHASE 5: FRONTEND INTEGRATION (Days 10-12)
### Focus: Wire UI to real API

### STEP 5.1: Update API Client
```typescript
// frontend/src/lib/api.ts

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const api = {
  market: {
    quote: async (symbol: string) => {
      const res = await fetch(`${API_BASE}/market/quote/${symbol}`);
      return res.json();
    },
    history: async (symbol: string, interval: string, period: string) => {
      const res = await fetch(
        `${API_BASE}/market/history/${symbol}?interval=${interval}&period=${period}`
      );
      return res.json();
    }
  },
  
  signals: {
    get: async (symbol: string) => {
      const res = await fetch(`${API_BASE}/signals/${symbol}`);
      return res.json();
    },
    bulk: async (symbols: string[]) => {
      const res = await fetch(`${API_BASE}/signals/bulk?symbols=${symbols.join(',')}`);
      return res.json();
    }
  },

  regime: {
    current: async () => {
      const res = await fetch(`${API_BASE}/regime/current`);
      return res.json();
    }
  }
};

// Before (mock)
export const api = {
  quote: async (symbol) => ({
    price: 2415.30,
    change: 10.50,
    // ...
  })
};
```

### STEP 5.2: Connect Hooks to Real WebSocket
```typescript
// frontend/src/hooks/usePriceFeed.ts

export function usePriceFeed(symbol: string) {
  const [quote, setQuote] = useState<Quote | null>(null);
  
  useEffect(() => {
    // Before: polling with interval
    // Wrong: const interval = setInterval(() => fetch(...), 1000);
    
    // Correct: WebSocket subscription
    const ws = new WebSocket(
      process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/prices'
    );
    
    ws.onopen = () => {
      ws.send(JSON.stringify({
        action: 'subscribe',
        symbols: [symbol]
      }));
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setQuote(data);
    };
    
    return () => ws.close();
  }, [symbol]);
  
  return quote;
}
```

### STEP 5.3: Build Complete Terminal Page
```typescript
// frontend/src/app/terminal/page.tsx

export default function TerminalPage() {
  const [selectedSymbol, setSelectedSymbol] = useState('RELIANCE.NS');
  
  return (
    <div className="grid grid-cols-[280px_1fr_320px] h-screen">
      {/* Left: Watchlist */}
      <Watchlist
        selectedSymbol={selectedSymbol}
        onSelect={setSelectedSymbol}
      />
      
      {/* Center: Chart */}
      <ChartSection symbol={selectedSymbol} />
      
      {/* Right: Signals */}
      <SignalPanel symbol={selectedSymbol} />
    </div>
  );
}

// ✅ Result: Terminal now displays REAL data from API
```

**Success Criteria:**
- ✅ Terminal loads real price data via API
- ✅ WebSocket price ticks update UI immediately
- ✅ Signal badges show real ensemble signals
- ✅ Regime pill shows current market state
- ✅ All responsive and smooth (60fps)

---

## PHASE 6: COMPLETE PAGES (Days 13-15)
### Focus: Build /markets, /research, /backtest, /portfolio

### STEP 6.1: Markets Page
```typescript
// frontend/src/app/markets/stocks/page.tsx

export default function StocksPage() {
  // Table showing all 40 symbols with:
  // - Ticker, Name, Price, Change%, Signal, Regime, 52w High/Low
  
  return (
    <div>
      <h1>Stock Universe (40 symbols)</h1>
      <StockTable
        columns={['Symbol', 'Price', 'Change%', 'Signal', 'PE Ratio', '52w High']}
        data={symbols}
        sortable
        filterable
      />
    </div>
  );
}
```

### STEP 6.2: Research Page
```typescript
// frontend/src/app/research/page.tsx

// Show 4 research sections:
// - Regime Analysis: HMM state probabilities over time
// - Correlation Graph: Asset correlation network (D3)
// - SHAP Explainability: Feature importance for selected asset
// - Model Performance: Accuracy, drift detection
```

### STEP 6.3: Backtest Lab
```typescript
// frontend/src/app/backtest-lab/page.tsx

// Allow users to:
// - Select strategy (Ensemble, TFT-only, MA-Crossover, etc.)
// - Choose universe and date range
// - Run backtest via POST /backtest/run
// - Display results: Sharpe, MaxDD, equity curve, trade log
```

---

## SUCCESS METRICS (After All Phases)

| Metric | Target | Status |
|--------|--------|---------|
| API response time | <150ms | ✅ |
| WebSocket latency | <50ms | ✅ |
| Model inference | <100ms | ✅ |
| Feature freshness | <1s | ✅ |
| UI responsiveness | 60fps | ✅ |
| Test coverage | 80%+ | ✅ |
| Database queries | <50ms P95 | ✅ |
| Uptime | 99.9% | ✅ |

---

## CRITICAL SUCCESS FACTOR

### DO NOT SKIP PHASE 1

Current state skipped:
- ❌ Database verification
- ❌ Data seeding
- ❌ Feature computation

Then tried to build everything on top of nothing.

**This roadmap fixes that:** Database → Data → Features → Models → API → WebSocket → Frontend

**Each phase depends on previous phase being 100% complete.**

---

## ESTIMATED TIMELINE

- Phase 1 (Foundation): 3 days
- Phase 2 (ML Training): 3 days
- Phase 3 (API): 2 days
- Phase 4 (WebSocket): 1 day
- Phase 5 (Frontend Integration): 3 days
- Phase 6 (Complete Pages): 3 days

**Total: 15 days for complete, working, professional platform**

Versus current state: "62 files that don't work = ∞ days"

---

## START NOW

```bash
# Right now, run:
docker-compose up timescaledb redis
cd backend && alembic upgrade head
psql postgresql://postgres:password@localhost:5432/algo_trading
\dt  # Verify 10 tables exist

# That's step 1. Everything else follows from there.
```
