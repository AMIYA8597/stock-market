# Stock Market Platform Blueprint (Phase 0-2)

## Phase 0: Requirements Extraction from new-prompt.txt

### Core Product Features
- Institutional trading terminal with watchlist, live signal feed, and regime-aware charting.
- Multi-market coverage: stocks, crypto, forex, macro data overlays.
- Research workbench: regime analysis, correlation graph, factor exposure, model diagnostics.
- Portfolio suite: holdings, performance, risk metrics, optimization workflows.
- Backtest lab: asynchronous run, status, and result analytics.
- Explainability suite: SHAP, attention visualization, counterfactual explanations.
- Alerting and model monitoring for drift, degradation, and operational health.

### Functional Requirements
- Authentication and role-aware access control for user workflows.
- Market data APIs for quote, history, indices, movers, heatmap, search.
- Signal APIs for single symbol, bulk symbols, and history.
- Regime APIs for current state, history, and statistical summaries.
- Portfolio transaction, holdings, performance, and risk endpoints.
- Backtest execution APIs with job lifecycle and result retrieval.
- Real-time channels for signal and price updates via WebSockets.

### Non-Functional Requirements
- Low-latency inference and responsive UI interactions.
- Fault-tolerant behavior when Redis/DB/dependencies are degraded.
- Strict type-safe contracts (frontend and backend models).
- Security posture aligned with OWASP and JWT best practices.
- Production observability: structured logs, metrics, health checks.
- Testability: unit + integration + contract verification.

### UI/UX Expectations
- Premium terminal visual language, not a beginner dashboard.
- Trading workflow support: buy/sell ticket, confidence/risk context, history.
- Mobile + desktop support with adaptive information density.
- Theme support (dark and light) with strong readability.
- Fast navigation between markets, research, backtest, portfolio, monitor.

### AI Requirements
- Multi-model architecture: TFT, HMM-GARCH, GNN, LSTM-attention, XGBoost.
- Ensemble weighting and confidence scoring with regime awareness.
- Risk-aware recommendation logic and portfolio optimization support.
- Explainability outputs exposed as first-class APIs.

## Phase 1: Stock Market App Research Synthesis

### Trading Flow (Operational Model)
- User selects symbol and receives current signal, regime, and confidence.
- User places BUY/SELL order through ticket with quantity/price controls.
- System computes transaction costs and confirms execution payload.
- Holdings, PnL, and risk snapshots update in near-real-time.

### Portfolio Management
- Consolidated holdings table with average cost, live price, unrealized PnL.
- Portfolio-level metrics: return, Sharpe, Sortino, beta, VaR/CVaR.
- Optimization methods exposed through constrained API workflows.

### Watchlist and Real-time
- Symbol watchlist remains always-visible for rapid context switching.
- Live signal and quote stream updates without full page reload.
- Degraded-mode UI states shown when stream quality drops.

### Charts and Indicators
- Time-series charting with regime/signal overlays and confidence context.
- Model weight and signal confidence visualization adjacent to chart.
- Extensible path for advanced indicators (RSI/MACD/MA) in chart section.

### AI Trading Use Cases
- Directional suggestions from ensemble signal.
- Position-size hints through Kelly fraction and confidence.
- Regime-aware risk interpretation for order decisions.
- Drift warnings to flag reliability concerns in model outputs.

## Phase 2: System Design Decision

### Architecture Decision
- Modular monolith with strict bounded modules, because the codebase already contains production-ready domain partitioning and shared contracts.
- FastAPI backend retained for real-time + quant workflow compatibility.
- Next.js frontend retained for app-router, SSR/CSR flexibility, and trading terminal UX.

### High-Level Data Flow
- Ingestion/services update market and feature layers.
- Model layer produces per-model outputs, then ensemble signal.
- Backend serves REST contracts and WebSocket streams.
- Frontend consumes contracts through typed client and incremental polling/streaming.

### API Contract Strategy
- Keep thin, typed frontend adapters for resilient shape normalization.
- Maintain route-level response models on backend for consistency.
- Track fallback behavior explicitly to preserve uptime in dev/test/degraded infra.

### Data Model Focus
- Users, symbols, ohlcv, feature vectors, predictions, ensemble signals.
- Portfolio holdings and transactions with auditable timestamps.
- Backtest jobs with asynchronous lifecycle states.
- Alerts and model drift metrics for operational controls.

## Immediate Execution Plan
1. Complete premium UI deltas first: theme switching, trading ticket, order history.
2. Validate frontend compile and runtime contract compatibility.
3. Continue remaining backend/AI/security hardening phases against this blueprint.
