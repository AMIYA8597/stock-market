════════════════════════════════════════════════════════════════════════════════
NEUROQUANT DEVELOPMENT ROADMAP — Phases 1-10 (Complete File Listing)
════════════════════════════════════════════════════════════════════════════════

This document specifies EVERY file that must be created for Phases 1-10.
Each phase is independent and must be fully completed before moving to the next.

════════════════════════════════════════════════════════════════════════════════
PHASE 0: ENVIRONMENT SETUP ✓ (COMPLETE)
════════════════════════════════════════════════════════════════════════════════
Status: COMPLETE
Files Created:
  ✓ scripts/setup.sh - One-command environment initialization
  ✓ infrastructure/postgres/init.sql - PostgreSQL 16 + TimescaleDB schema
  ✓ backend/alembic/versions/0001_initial_schema.py - Alembic migration

Next: PHASE 1 DATABASE

════════════════════════════════════════════════════════════════════════════════
PHASE 1: DATABASE + MIGRATIONS ◀ CURRENT PHASE
════════════════════════════════════════════════════════════════════════════════
Status: IN PROGRESS
Completion: 20% (SQL ✓, Alembic migration ✓)
Remaining Work:
  - Run alembic upgrade head
  - Verify all tables created
  - Create Redis config

Files To Create:
  1. infrastructure/redis/redis.conf
     Purpose: Redis Sentinel + caching configuration
     Key settings: binding, port 6379, cluster-enabled no, save "", maxmemory 2gb, maxmemory-policy allkeys-lru
     
  2. Test file: backend/tests/test_phase1_database.py
     Purpose: Verify database schema created correctly
     Tests: 
       - All 12 tables exist
       - All indices created
       - TimescaleDB hypertables configured
       - User can authenticate after insertion
     
Test Command After This Phase:
  cd backend
  alembic upgrade head
  python -m pytest tests/test_phase1_database.py -v

════════════════════════════════════════════════════════════════════════════════
PHASE 2: AUTHENTICATION SERVICE
════════════════════════════════════════════════════════════════════════════════
Status: QUEUED

Files To Create (Backend/Gateway):
  1. services/gateway/app/core/config.py (200 lines)
     - Pydantic Settings config
     - JWT config (RS256 keys path, expiry times)
     - Database URL, Redis URL
     - CORS origins whitelist
     - Password policy (min entropy, zxcvbn)
     
  2. services/gateway/app/core/security.py (400 lines)
     - JWT token creation & verification (RS256)
     - Argon2id password hashing (memory=64MB, iterations=3)
     - Fernet field encryption (AES-256-GCM)
     - TOTP setup & verification (RFC 6238)
     - Refresh token family tracking
     
  3. services/gateway/app/models/user.py (150 lines)
     - SQLAlchemy User model
     - RefreshToken model
     - BackupCode model
     
  4. services/gateway/app/schemas/auth.py (150 lines)
     - RegisterRequest, LoginResponse
     - TOTP SetupResponse, VerifyTOTPRequest
     - Token schemas
     
  5. services/gateway/app/api/v1/auth.py (500 lines)
     - POST /register (with email verification)
     - POST /login (with 2FA check)
     - POST /refresh (with token rotation)
     - POST /logout (blacklist JTI)
     - POST /2fa/setup
     - POST /2fa/verify
     - POST /password-reset
     
  6. services/gateway/app/core/database.py (100 lines)
     - Async SQLAlchemy engine + session factory
     - Connection pooling (pool_size=20, max_overflow=10)
     
  7. services/gateway/tests/test_auth.py (300 lines)
     - Test registration flow
     - Test login with argon2 verification
     - Test TOTP 2FA setup & verify
     - Test refresh token rotation
     - Test password lockout after 5 attempts

Test Command: pytest services/gateway/tests/test_auth.py -v

════════════════════════════════════════════════════════════════════════════════
PHASE 3: DATA PIPELINE (Ingestion + Real-Time)
════════════════════════════════════════════════════════════════════════════════
Status: QUEUED

Files To Create:
  1. services/data-pipeline/app/ingestion/yfinance_fetcher.py (250 lines)
     - Historical data fetch for NSE300 + S&P100 + Top20 Crypto
     - Bulk load into PostgreSQL (COPY for 1M+ rows in <1s)
     - TimescaleDB OHLCV table insert
     
  2. services/data-pipeline/app/ingestion/nsepy_fetcher.py (150 lines)
     - NSE-specific data (F&O, indices, options chains)
     - High-frequency tick data if available
     
  3. services/data-pipeline/app/scheduler/market_hours.py (100 lines)
     - APScheduler configuration
     - 1-minute refresh during market hours (9:15 AM - 3:30 PM IST)
     - 15-minute refresh during US hours
     
  4. services/data-pipeline/app/streaming/price_simulator.py (150 lines)
     - During market hours: real API data
     - Off hours: realistic price walk (Brownian motion)
     - Publishes to Redis Pub/Sub every second
     
  5. services/data-pipeline/app/core/pubsub.py (100 lines)
     - Redis Pub/Sub publisher
     - Publish format: {"type": "tick", "symbol", "price", "volume", "timestamp"}
     
  6. services/gateway/app/core/redis_pubsub.py (100 lines)
     - Subscribe to Redis channels
     - Connection management
     
  7. services/data-pipeline/tests/test_ingestion.py (300 lines)
     - Test yfinance fetcher returns correct columns
     - Test bulk insert speed > 100K rows/sec
     - Test TimescaleDB compression works

Test Command: 
  cd services/data-pipeline
  python -m pytest tests/test_ingestion.py -v
  # Verify ticks flowing: redis-cli SUBSCRIBE "ticks:RELIANCE.NS"

════════════════════════════════════════════════════════════════════════════════
PHASE 4: FEATURE ENGINEERING + ML MODEL TRAINING
════════════════════════════════════════════════════════════════════════════════
Status: QUEUED

Files To Create:
  1. services/ml-engine/app/features/feature_engineer.py (800 lines)
     - 31 core features: SMA, EMA, RSI, MACD, BB, ATR, Volume, ...
     - 61 TA-Lib candlestick patterns
     - Cross-asset features (Beta, Correlation, GNN), Ichimoku
     - Hurst exponent, Fractal dimension, Entropy
     - tsfresh integration (500+ features)
     - Feature scaling (RobustScaler)
     - Output: (n_samples, 200) feature DataFrame
     
  2. services/ml-engine/app/features/technical_indicators.py (400 lines)
     - pd-ta wrapper functions
     - All the technical indicators (SMA, EMA, MACD, RSI, etc.)
     
  3. services/ml-engine/app/models/amstan.py (600 lines)
     - PyTorch AMSTAN transformer model
     - Multi-scale patch embedding (5/20/60 bars)
     - Regime-gated attention
     - Cross-asset attention
     - Monte Carlo dropout for uncertainty
     - Outputs: price, direction, confidence, 80%/95% intervals
     
  4. services/ml-engine/app/models/ensemble.py (300 lines)
     - XGBoost, LightGBM, CatBoost wrappers
     - Stacking meta-learner
     - feature importances via SHAP
     
  5. services/ml-engine/app/models/hmm_regime.py (200 lines)
     - HMM regime detection (Bull/Bear/Sideways)
     - Training on 60-day rolling returns
     - Transition probability matrix
     
  6. services/ml-engine/app/training/train_pipeline.py (400 lines)
     - Data loading from PostgreSQL
     - Walk-forward CV (5 splits)
     - AMSTAN trainer (PyTorch Lightning)
     - Ensemble training
     - Model registry to MLflow
     
  7. services/ml-engine/app/inference/predictor.py (200 lines)
     - Load trained models
     - Generate predictions for new data
     - Monte Carlo uncertainty (T=50)
     - Return PredictionOutput with all fields
     
  8. services/ml-engine/tests/test_ml.py (400 lines)
     - Test feature extraction shape (n, 200)
     - Test AMSTAN inference speed < 500ms
     - Test uncertainty intervals calibration
     - Test regime detection accuracy > 60%
     - Test ensemble prediction shape
     
  9. services/ml-engine/requirements.txt
     - torch, lightning, transformers, scikit-learn
     - xgboost, lightgbm, catboost
     - pandas-ta, ta-lib, tsfresh, statsmodels
     - shap, optuna, mlflow

Test Command:
  cd services/ml-engine
  python -m pytest tests/test_ml.py -v
  # Verify inference: python -c "from app.inference import predictor; ..."

════════════════════════════════════════════════════════════════════════════════
PHASE 5: RISK ENGINE (VaR, CVaR, Portfolio Optimization)
════════════════════════════════════════════════════════════════════════════════
Status: QUEUED

Files To Create:
  1. services/risk-engine/app/metrics/var_calculation.py (300 lines)
     - Historical VaR (percentile method)
     - Parametric VaR (assume normal distribution)
     - Cornish-Fisher VaR (4th moment adjustment)
     - CVaR (expected shortfall)
     - Backtesting: traffic light approach
     
  2. services/risk-engine/app/metrics/monte_carlo.py (250 lines)
     - Monte Carlo portfolio simulation (1000 paths, 252 days)
     - Cholesky decomposition for correlation
     - Output: probability of reaching targets, drawdown quantiles
     
  3. services/risk-engine/app/optimization/portfolio_opt.py (400 lines)
     - Mean-Variance Optimization (Markowitz)
     - Hierarchical Risk Parity (HRP)
     - Black-Litterman with views
     - Efficient frontier computation
     - Constraint handling: sector limits, position limits
     
  4. services/risk-engine/app/optimization/kelly_criterion.py (150 lines)
     - Kelly % calculation from historical win rate
     - Volatility-scaled position sizing
     - Fractional Kelly (safer, 25%)
     
  5. services/risk-engine/app/stress_testing.py (200 lines)
     - Historical stress scenarios
     - Hypothetical stress (2008-style crash, interest rate spike)
     - Correlation breakdown scenarios
     
  6. services/risk-engine/tests/test_risk.py (300 lines)
     - Test VaR = 0 for zero portfolio
     - Test CVaR > VaR always
     - Test efficient frontier is monotonic in Sharpe
     - Test stress test P&L magnitude

Test Command:
  cd services/risk-engine
  python -m pytest tests/test_risk.py -v

════════════════════════════════════════════════════════════════════════════════
PHASE 6: BACKTESTING ENGINE (Event-driven, 6 Strategies)
════════════════════════════════════════════════════════════════════════════════
Status: QUEUED

Files To Create:
  1. services/backtesting/app/base/event.py (100 lines)
     - Event classes: MarketEvent, SignalEvent, OrderEvent, FillEvent
     
  2. services/backtesting/app/base/portfolio.py (400 lines)
     - Portfolio initialization from base amount
     - Order execution with slippage + commissions (0.05% typical)
     - Position tracking, P&L calculation
     - Holdings by sector/symbol
     
  3. services/backtesting/app/data/data_handler.py (200 lines)
     - Load OHLCV from PostgreSQL
     - Generate bar events in order
     
  4. services/backtesting/app/base/strategy.py (200 lines)
     - AbstractStrategy class
     - generate_signals() method (returns +1/-1/0 Series)
     - get_params() for optimization
     
  5. services/backtesting/app/strategies/kalman_pairs.py (300 lines)
     - Cointegration test (Engle-Granger + Johansen)
     - Kalman Filter hedge ratio estimation
     - Entry/exit on spread z-score
     
  6. services/backtesting/app/strategies/adaptive_momentum.py (250 lines)
     - Dual momentum (absolute + relative)
     - HMM regime filter
     - Volatility parity position sizing
     
  7. services/backtesting/app/strategies/ml_alpha.py (200 lines)
     - AMSTAN prediction signal
     - Sentiment weighting
     - MVO portfolio construction
     
  8. services/backtesting/app/strategies/stat_arb.py (200 lines)
     - Index rebalancing strategy
     - Track NSE additions/deletions
     - Price pressure model
     
  9. services/backtesting/app/strategies/volatility_regime.py (150 lines)
     - GARCH regime detection
     - Momentum in low vol, mean-reversion in high vol
     
  10. services/backtesting/app/strategies/drl_agent.py (150 lines)
      - PPO agent trained via stable-baselines3
      - StockTradingEnv
      
  11. services/backtesting/app/performance/metrics.py (300 lines)
      - CAGR, Sharpe, Sortino, Calmar
      - Max Drawdown, Win Rate, Profit Factor
      - Walk-forward results
      
  12. services/backtesting/app/performance/significance.py (250 lines)
      - Monte Carlo permutation test (p-value)
      - Bootstrap Sharpe CI
      - Deflated Sharpe Ratio
      
  13. services/backtesting/app/output/report_generator.py (200 lines)
      - WeasyPrint PDF generation
      - Charts, tables, summary metrics
      
  14. services/backtesting/tests/test_backtest.py (400 lines)
      - Test momentum strategy 2020-2024: Sharpe > 0.5
      - Test buy-and-hold baseline
      - Test order execution with slippage

Test Command:
  cd services/backtesting
  python -m pytest tests/test_backtest.py::test_momentum_sharpe -v

════════════════════════════════════════════════════════════════════════════════
PHASE 7: FASTAPI REST ENDPOINTS (Gateway Service)
════════════════════════════════════════════════════════════════════════════════
Status: QUEUED

Files To Create:
  1. services/gateway/app/api/v1/market.py (200 lines)
     - GET /ohlcv/{symbol}?start=...&end=...&interval=1m|1h|1d
     - GET /quote/{symbol} (latest price + metrics)
     - GET /index/{index_symbol} (Nifty50, Sensex, etc.)
     - GET /search/symbols?q=... (symbol search via Meilisearch)
     - GET /screener/results (with filter list)
     
  2. services/gateway/app/api/v1/predictions.py (200 lines)
     - GET /predictions/{symbol}?horizon=5|10|30
     - GET /predictions/top (top 10 predicted winners)
     - GET /predictions/leaderboard (model performance)
     - POST /predictions/batch (request predictions for multiple symbols)
     
  3. services/gateway/app/api/v1/portfolio.py (300 lines)
     - GET /portfolios (list user's portfolios)
     - POST /portfolios (create new portfolio)
     - GET /portfolios/{id}/holdings
     - POST /portfolios/{id}/holdings (add holding)
     - DELETE /portfolios/{id}/holdings/{holding_id}
     - GET /portfolios/{id}/risk (VaR, CVaR, Sharpe)
     - POST /portfolios/{id}/optimize (efficient frontier)
     - POST /portfolios/{id}/rebalance
     
  4. services/gateway/app/api/v1/screener.py (200 lines)
     - POST /screener/run (execute filter set)
     - GET /screener/presets (return preset screens)
     - POST /screener/save (save custom screen)
     
  5. services/gateway/app/api/v1/backtesting.py (250 lines)
     - POST /backtest/run (submit backtest job)
     - GET /backtest/{run_id} (get results)
     - GET /backtest/{run_id}/trades (trade log)
     - GET /backtest/{run_id}/report/pdf
     
  6. services/gateway/app/api/v1/alerts.py (200 lines)
     - POST /alerts (create alert definition)
     - GET /alerts (list active alerts)
     - DELETE /alerts/{alert_id}
     - GET /alerts/history (past triggered alerts)
     
  7. services/gateway/app/api/v1/research.py (150 lines)
     - POST /research/generate/{symbol} (trigger LangGraph agent)
     - GET /research/{request_id} (get report status/result)
     
  8. services/gateway/app/api/v1/health.py (50 lines)
     - GET /health (database + Redis + services ping)
     
  9. services/gateway/app/middleware/rate_limit.py (100 lines)
     - slowapi rate limiting
     - @limiter.limit("1000/minute") on endpoints
     - Auth endpoints: 5/minute
     
  10. services/gateway/app/middleware/audit_log.py (150 lines)
      - Log every API call to audit_log table
      - Include user, endpoint, params, response status
      - Immutable append-only
      
  11. services/gateway/app/middleware/security_headers.py (80 lines)
      - Content-Security-Policy, HSTS, X-Frame-Options, etc.
      
  12. services/gateway/app/cache/redis_cache.py (100 lines)
      - Cache market data for 5 minutes
      - Cache predictions for 1 hour
      - Cache leaderboard for 1 hour
      
  13. services/gateway/tests/test_api.py (400 lines)
      - Test all endpoints: 90%+ coverage
      - Test rate limiting
      - Test audit logging
      - Test RBAC: analyst can't access /admin endpoints

Test Command:
  cd services/gateway
  python -m pytest tests/test_api.py -v --cov=app --cov-report=term-missing
  # Coverage must be >= 90%

════════════════════════════════════════════════════════════════════════════════
PHASE 8: WEBSOCKET SERVER + Redis Pub/Sub
════════════════════════════════════════════════════════════════════════════════
Status: QUEUED

Files To Create:
  1. services/gateway/app/websocket/connection_manager.py (300 lines)
     - Per-user connection registry (Dict[UUID, List[WebSocket]])
     - Per-symbol subscription registry (Dict[symbol, Set[UUID]])
     - Heartbeat logic (30s ping, 10s timeout)
     - Concurrent connections limit (10 per user)
     - Auto-cleanup on disconnect
     
  2. services/gateway/app/websocket/message_types.py (100 lines)
     - Pydantic models for all message types
     - TickMessage, PredictionMessage, AlertMessage, etc.
     
  3. services/gateway/app/api/v1/ws.py (400 lines)
     - POST /ws?token={jwt_token} (WebSocket endpoint)
     - Handle: subscribe, unsubscribe, pong messages
     - Send: tick, prediction, alert, regime, anomaly, portfolio, heartbeat
     - Auto-reconnection support on client
     
  4. services/gateway/app/websocket/pubsub_handler.py (200 lines)
     - Redis Pub/Sub subscriber
     - Listen on topics: ticks:*, predictions:*, alerts
     - Forward to connected clients based on subscriptions
     
  5. services/data-pipeline/app/streaming/publish_ticks.py (100 lines)
     - Publish ticks to Redis every second
     - Format: {"type": "tick", "symbol": "...", "price": ..., ...}
     
  6. services/gateway/tests/test_websocket.py (300 lines)
     - Test 3 clients connect + subscribe to symbols
     - Test tic delivery within 100ms
     - Test reconnection backoff (1s → 2s → 4s → ...).
     - Test heartbeat timeout disconnect

Test Command:
  cd services/gateway
  python -m pytest tests/test_websocket.py -v
  # Manual: wscat -c "ws://localhost:8000/ws?token=<jwt>"

════════════════════════════════════════════════════════════════════════════════
PHASE 9: LANGGRAPH MULTI-AGENT SYSTEM
════════════════════════════════════════════════════════════════════════════════
Status: QUEUED

Files To Create:
  1. services/gateway/app/agents/news_agent.py (200 lines)
     - Fetch latest news for symbol via NewsAPI
     - FinBERT sentiment classification
     - Summarize top 5 news items
     
  2. services/gateway/app/agents/technical_agent.py (200 lines)
     - Identify candle patterns (61 TA-Lib patterns)
     - Support/resistance levels
     - Generate technical view report
     
  3. services/gateway/app/agents/fundamental_agent.py (200 lines)
     - Fetch fundamentals from API (P/E, PB, ROE, etc.)
     - DCF valuation
     - Peer comparison (top 5)
     
  4. services/gateway/app/agents/risk_agent.py (150 lines)
     - Volatility metrics
     - Drawdown risk
     - Sector risk exposure
     
  5. services/gateway/app/agents/orchestrator.py (200 lines)
     - LangGraph state machine
     - Call all 4 agents in parallel
     - Aggregate results into single report
     - Contradiction detection
     
  6. services/gateway/app/api/v1/research.py (endpoint)
     - POST /research/generate/{symbol}
     - Trigger orchestrator
     - Return LLM-formatted report with markdown
     
  7. services/gateway/tests/test_agents.py (250 lines)
     - Test news agent returns 5+ items
     - Test technical patterns detected correctly
     - Test orchestrator combines all sections

Test Command:
  cd services/gateway
  python -m pytest tests/test_agents.py::test_orchestrator -v

════════════════════════════════════════════════════════════════════════════════
PHASE 10: NEXT.JS FRONTEND SETUP
════════════════════════════════════════════════════════════════════════════════
Status: QUEUED

Files To Create:
  1. apps/web/tsconfig.json
     - strict: true, all strict flags
     - target: ES2020
     - module: ESNext
     - jsx: preserve (for Next.js)
     - moduleResolution: node
     - noUncheckedIndexAccess: true
     
  2. apps/web/next.config.js
     - appDir: true (App Router)
     - typescript: { strict: true }
     - swcMinify: true
     - productionBrowserSourceMaps: false
     - reactStrict: true
     
  3. apps/web/tailwind.config.js
     - Dark mode: class  
     - Colors: custom theme with design tokens
     - Extend: custom animations, fonts
     
  4. apps/web/src/lib/api.ts (150 lines)
     - axios instance with interceptors
     - Auto-add JWT to Authorization header
     - Error handling + 401 refresh token logic
     - TypeScript request/response types
     
  5. apps/web/src/lib/auth.ts (100 lines)
     - NextAuth.js v5 configuration
     - Credentials provider (username+password)
     - Google OAuth provider
     - JWT callback
     
  6. apps/web/src/app/layout.tsx (80 lines)
     - Global fonts (Clash Display, JetBrains Mono, Cabinet Grotesk)
     - NextAuth SessionProvider
     - Metadata
     
  7. apps/web/src/app/login/page.tsx (200 lines)
     - Email + password form
     - TOTP 2FA input (conditional)
     - OAuth buttons (Google)
     
  8. apps/web/src/app/dashboard/layout.tsx (100 lines)
     - Sidebar navigation
     - Top navigation bar
     
  9. apps/web/src/types/market.ts (150 lines)
     - TickData, PredictionData, AlertEvent, etc.
     - WebSocketMessage types
     
  10. apps/web/src/hooks/useWebSocket.ts (300 lines)
      - WebSocket connection + auth
      - Exponential backoff reconnection
      - Per-symbol subscriptions
      - Message type handling
      
  11. apps/web/src/components/common/Header.tsx (150 lines)
      - Navigation bar (Dashboard, Screener, Portfolio, Research, Alerts)
      - Search (Cmd+K)
      - Notifications
      - Connection status
      
  12. apps/web/src/components/dashboard/TickerStrip.tsx (120 lines)
      - 7 tickers with live prices + sparklines
      - WebSocket subscriptions
      - Color-coded changes
      
  13. apps/web/src/components/dashboard/Heatmap.tsx (300 lines)
      - D3.js treemap NSE500
      - Color gradient
      - Hover tooltips
      
  14. apps/web/src/components/dashboard/AISummaryPanel.tsx (280 lines)
      - Regime badge
      - AI analysis (3 paragraphs)
      - Fear & Greed gauge
      - Catalyst events
      
  15. apps/web/src/app/dashboard/page.tsx (150 lines)
      - Grid layout (12 cols)
      - All dashboard components
      
  16. apps/web/package.json
      - next@14.2, react@18.3, typescript@5.4
      - tailwindcss, radix-ui, zustand, @tanstack/react-query
      - vitest, @testing-library/react, @playwright/test
      
  17. apps/web/tests/dashboard.test.tsx (100 lines)
      - Username: can navigate to dashboard
      - Ticker strip renders
      - WebSocket connection established

Test Command:
  cd apps/web
  pnpm dev
  # Visit http://localhost:3000 → login → dashboard loads

════════════════════════════════════════════════════════════════════════════════
SUMMARY: PHASES 1-10
════════════════════════════════════════════════════════════════════════════════

Total Files to Create: 75+
Total Lines of Code: ~15,000

Phases 1-5: Backend Infrastructure (5,000 lines)
  - Database, Auth, Data, ML, Risk

Phases 6-8: Execution & Communication (4,000 lines)
  - Backtesting, REST API, WebSocket

Phase 9: AI Intelligence (1,000 lines)
  - LangGraph multi-agent system

Phase 10: Frontend Bootstrap (2,000 lines)
  - Next.js, auth, dashboard

All phases are INDEPENDENT and can be developed in parallel,
but testing requires dependencies (e.g., Phase 7 needs Phase 2, 3, 4, 5).

════════════════════════════════════════════════════════════════════════════════
