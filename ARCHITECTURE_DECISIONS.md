# Architecture Decisions

## 1. Data Layer: yfinance Primary with Strict NSE Fallback
**Context:** Indian equities data is notoriously difficult to acquire affordably with real-time ticks. 
**Decision:** We use `yfinance` as the primary data source, rate-limited to 2 requests per second (burst 5) via a TokenBucket semaphore to respect undocumented limits.
**Tradeoffs:** `yfinance` is an unofficial scraper and can fail or rate-limit unpredictably. To defend against this, we have a strict, honest `IndianStockAPI` fallback. If both fail, the system explicitly throws a 503 rather than serving stale or fabricated "mock" data. This aligns with the "Honesty Law".

## 2. ML Layer: The Honesty Law & >75% Leakage Guard
**Context:** Financial ML is highly susceptible to look-ahead bias and feature leakage, often leading to unrealistic backtest results.
**Decision:** A hardcoded guard exists in `training_pipeline.py`. If walk-forward validation accuracy exceeds 75%, the system immediately halts and rejects the deployment. 
**Tradeoffs:** We sacrifice "perfect" theoretical models in favor of guaranteeing that any deployed model is strictly bounded by realistic market efficiency constraints. 

## 3. Signal Fusion: Regime-Gated Rule
**Context:** Technical indicators fail during structural breaks, while ML models can overfit to specific regimes.
**Decision:** We use an HMM-GARCH regime detection layer. The final signal fusion (`0.4 * tech + 0.6 * ML + sentiment`) is dynamically gated based on the current detected regime (e.g., trend vs. mean-reverting).
**Tradeoffs:** Increases inference latency slightly due to HMM state decoding, but drastically reduces drawdown during regime shifts.

## 4. NLP: Local FinBERT over Hosted Inference
**Context:** We need sentiment analysis on financial news.
**Decision:** We run `ProsusAI/finbert` locally using `transformers` rather than calling OpenAI or huggingface APIs.
**Tradeoffs:** Higher memory footprint on the backend container, but guarantees zero marginal cost per request, zero latency spikes, and complete data privacy.
**Limitation / Honesty Rule:** FinBERT measures "tone" (e.g. positive/negative wording) which does NOT reliably equal "price-impact". A headline can be highly negative in tone but fully priced-in, or even structurally bullish for a specific asset class. Because of this known mapping fragility, the sentiment `scale factor` in the signal fusion rule is hardcoded to a deliberately conservative **0.15** maximum tilt. This weight must NOT be casually increased without new walk-forward statistical evidence proving tone maps to directional alpha.

## 5. Hosting: Fly.io over Vercel/Heroku
**Context:** The terminal UI requires a real-time price and prediction overlay.
**Decision:** We deploy the backend to Fly.io rather than standard serverless providers.
**Tradeoffs:** Fly.io supports long-lived, stateful WebSockets natively on their edge nodes. Serverless platforms (like Vercel functions) have strict timeout limits and do not support true WebSockets, which would force us to use expensive polling. Fly.io's pricing structure allows for an affordable hobby-tier Redis + WebSocket setup.

## 6. Charting: lightweight-charts v5
**Context:** The chart is the most critical UI element. In v4, sub-panes (RSI, MACD, ATR) required hand-rolled synchronization of multiple separate `createChart` instances, leading to resize glitches and complex React refs.
**Decision:** We migrate to `lightweight-charts` v5. v5 introduces native multi-pane support, allowing all series to live in a single chart instance, radically simplifying `useChartInstance.ts` and `subpaneRenderer.ts`.
**Tradeoffs:** Requires adapting to breaking changes in the API (e.g. series creation) but vastly reduces our custom charting code footprint and improves rendering performance by eliminating React `ResizeObserver` sync loops.
