# ROADMAP

Starting state: main = b5dc119 (CI green, deployed). PR #27 (phase/1-auth-envs-e2e) is open with the
e2e check FAILING. Known backlog: /market/indices and /market/global-context take 7-12 s;
regime_state is "unknown" for every index (the regime job never ran); signals fall back when models
are untrained; apps/web/src/tests/safety.test.ts fails on main and is not in CI; Playwright output
folders are tracked in git; one-off scripts clutter the repo root; local backend/.env points at the
production database; the DB password is in git history (commit a9ea2f6); SendGrid, Upstox tokens
and Razorpay webhook secret are empty.

## PHASE 1 — Finish auth / environments / E2E (PR #27)
Verified failures: 6 of 12 Playwright tests fail.
- auth.spec.ts doesn't match the real UI: register heading is "Register" (not "Create Account");
  login is TWO steps (email -> "Continue" -> password); wrong password shows "Incorrect password."
- Every redirect to /dashboard fails because middleware.ts needs a real Supabase session cookie.
- onboarding.spec.ts (pre-existing) sets fake "sb-access-token" cookies that @supabase/ssr never reads.
- smoke.yml can never run: playwright.config.ts testIgnore '**/smoke.spec.ts' means
  `playwright test e2e/smoke.spec.ts` finds 0 tests, and the default config starts local webServers.

Tasks:
- [x] Read register/page.tsx, login/page.tsx, middleware.ts and the onboarding page first.
- [x] apps/web/e2e/helpers/session.ts: build the session cookie exactly as the installed @supabase/ssr
    stores it (name sb-<project-ref>-auth-token from NEXT_PUBLIC_SUPABASE_URL; encoding and chunking
    as implemented in node_modules/@supabase/ssr; read it, don't guess) with an unsigned JWT,
    exp = now + 1h; plus page.route('**/auth/v1/user') returning a fake user so setSession() works offline.
- [x] Rewrite auth.spec.ts: register token path -> /en/dashboard; register login_required ->
    /en/login?registered=1 with "Account created. Please sign in." on the password step;
    register OTP path -> "Verify Your Email" -> verify -> /en/dashboard; password mismatch and weak
    password errors; login two-step happy path; unknown email -> "Account not found";
    wrong password -> "Incorrect password."; 403 -> verify step; 429 -> lockout message;
    protected route while logged out -> /en/login.
- [x] Fix onboarding.spec.ts with the same helper.
- [x] apps/web/playwright.smoke.config.ts (testMatch smoke.spec.ts, baseURL from SMOKE_TARGET_URL,
    no webServer, retries 1). smoke.yml uses it, needs only SMOKE_TEST_EMAIL / SMOKE_TEST_PASSWORD,
    and exits 0 with a ::notice when they are missing. Remove SMOKE_API_URL, SMOKE_WS_URL and the
    NEXT_PUBLIC_* env from smoke.yml and docs/ENVIRONMENTS.md. Smoke spec uses the real two-step login.
- [x] Untrack apps/web/playwright-report/ and apps/web/test-results/ (.gitignore + git rm -r --cached).
- [x] Run the whole E2E suite locally with CI's env and --retries=0: 100% green. Run the smoke config
    with --list: exactly 2 tests. Paste both outputs.

GATE 1: PR #27 all checks green and merged; smoke workflow skips cleanly until I add its secrets.

## PHASE 2 — Monorepo and repo hygiene
- [x] It is already a pnpm + turbo monorepo. Add the backend to it without moving the folder
    (Cloud Run deploy and the Dockerfile depend on backend/): backend/package.json scripts
    (dev, lint, typecheck, test) wrapping uv; turbo pipelines so `pnpm dev` starts API + web
    and `pnpm lint`, `pnpm typecheck`, `pnpm test` run everything.
- [x] docker-compose.dev.yml provides Postgres + Redis; one documented command starts the whole stack
    locally; LOCAL_SETUP.md updated and tested from a fresh clone.
- [x] Clean the root and backend/: one-off scripts (fix_*.py, append_*.py, patch_e2e.py, clean_junk.py,
    test_login.js, generate_i18n.py, backend fix_*.py, rewrite_detect_regime.py), out*.txt, test_out.txt,
    duplicate audit/report markdowns -> delete or move to archive/ AFTER grepping that nothing uses them.
- [x] Dependabot (pip, npm, github-actions), CODEOWNERS, PR template; list the exact GitHub
    branch-protection settings for main (required checks) for me to click.
- [x] Bump GitHub Actions off deprecated Node 20 versions.

GATE 2: fresh clone -> documented commands -> app runs locally on the local DB; all checks green.

## PHASE 3 — Every page, 10 kinds of testing
For every route under apps/web/src/app/[locale]:
 1 unit  2 API integration  3 contract (openapi.json vs frontend types; CI fails if openapi.json is stale)
 4 E2E (Playwright + session helper)  5 visual (desktop + mobile snapshots)
 6 accessibility (axe: no serious/critical)  7 performance (LCP; API p95; cache /market/indices and
 /market/global-context)  8 security/authz (every endpoint: anonymous, other user, owner, admin)
 9 data quality (prices/candles match source, not stale, IST timestamps, no fabricated values)
 10 resilience (backend down, empty data, 401/403/404/429/503 shown clearly, never a blank page).
- [ ] Fix apps/web/src/tests/safety.test.ts (its regex is broken) and add it to CI.
- [ ] docs/QA_MATRIX.md: route x test type = pass/fail + evidence; fix every failure.

GATE 3: QA matrix all pass; production has 0 console errors and 0 5xx on every route;
core API p95 < 1.5 s (measured).

## PHASE 4 — Market data
- [ ] Upstox analytics token (I provide) for live quotes/candles; Stooq/yfinance fallback; caching;
    rate limits; NSE holidays and market hours (IST).
- [ ] Scheduled ingestion (Cloud Scheduler or Celery beat; choose and justify) + data-quality checks
    with alerts.
- [ ] Advanced charts: candles, Heikin-Ashi, Renko, volume profile, multi-timeframe; indicators
    (VWAP, EMA, ADX/DI, RSI, MACD, Supertrend, Bollinger, ATR) computed server-side and tested
    against pandas-ta.

GATE 4: 30 days of clean OHLCV for NIFTY 50 constituents + indices; data-quality report green.

## PHASE 5 — AI/ML models
- [ ] Inventory every model that really exists (research/, backend/app/services/ml_engine:
    HMM-GARCH regime, XGBoost, LSTM-attention, GNN, ensemble meta-learner, online learner, SARIMAX,
    BiLSTM support/resistance, sentiment, SHAP explanations).
- [ ] For each: training pipeline, leakage tests, walk-forward / purged CV, versioned artifacts,
    scheduled retraining, drift monitoring, model card (data, features, out-of-sample metrics vs
    naive baselines, failure modes) in docs/models/.
- [ ] Schedule the regime job so regime_state is real. UI labels fallback signals as fallbacks.
- [ ] Remove or flag any model that does not beat its naive baseline out-of-sample, and say so.

GATE 5: every model shown in the UI has a model card with measured out-of-sample results.

## PHASE 6 — Strategies and backtesting
- [ ] Port my TradingView strategy "EMA 9/21 + VWAP + ADX" as a deterministic strategy:
    LONG signal candle = EMA9 crosses above EMA21, both EMAs above session VWAP (daily-anchored),
    ADX(14) > 20 on that candle. Entry = buy-stop one tick above the signal candle's high; if not hit,
    move the stop to each newly closed candle's high until filled; cancel on the opposite crossover.
    SL = lowest low of last 3 bars minus 0.1*ATR(14), minimum SL distance 0.3*ATR; TP = 3R;
    fixed risk per trade; one trade at a time. SHORT is the exact mirror.
- [ ] Port the "EMA 50 retest" variant as a second strategy (touch tolerance 0.3*ATR, move-away 1*ATR
    before a new retest, bounce candle within 3 bars, optional 15-min EMA-50 trend + slope filter,
    optional ADX filter, optional break-of-both-EMAs rule), with stats by retest number.
- [ ] Backtest engine: next-bar fills, no lookahead, Indian costs (brokerage, STT, exchange fees,
    SEBI fee, GST, stamp duty), slippage, walk-forward, many symbols and market regimes.
- [ ] Compare: both rule strategies, ML signals, the ensemble, buy-and-hold NIFTY 50.
    Report CAGR, Sharpe with confidence interval / deflated Sharpe, Sortino, max drawdown,
    profit factor, expectancy per trade, win rate with confidence interval, trade count, exposure.
- [ ] docs/STRATEGY_REPORT.md, reproducible with one command. If nothing beats buy-and-hold after
    costs, the report says so plainly.

GATE 6: report reproducible; results stored in the DB and shown in the Backtest Lab UI.

## PHASE 7 — Automated PAPER trading
- [ ] Signal -> risk checks -> paper order -> realistic fill (next bar/tick, slippage, costs) ->
    positions -> P&L, fully automatic for the best validated strategy.
- [ ] Risk engine: risk % per trade, max position size, max open positions, sector/exposure caps,
    max daily loss, max drawdown stop, cooldown after losses, market-hours guard, kill switch.
- [ ] Audit log, daily report (email/notification), live-paper vs backtest dashboard.

GATE 7: runs unattended >= 8 weeks; kill-switch drill done; live-paper results inside the backtest's
confidence band, or the report explains why not.

## PHASE 8 — Security, reliability, compliance, release
- [ ] docs/SECURITY_CHECKLIST.md: OWASP ASVS Level 2, evidence per item.
- [ ] Supabase RLS policies tested; authz tests from Phase 3 in CI; rate limits; CSP and security headers.
- [ ] Secrets only in GitHub Secrets / Vercel / Cloud Run; rotate the DB password in git history
    (commit a9ea2f6) and any other exposed key (tell me the steps; I rotate them).
- [ ] CI: pip-audit, pnpm audit, gitleaks, CodeQL; no open high/critical findings.
- [ ] Sentry, uptime monitoring and alerts; DB backups + a tested restore; incident runbook.
- [ ] Privacy policy, terms, "not investment advice" disclaimers. List the questions I must ask a
    lawyer: whether showing buy/sell signals to the public needs SEBI Research Analyst registration,
    and what SEBI's retail algo-trading rules require.
- [ ] CHANGELOG.md, tag v1.0.0, docs/RELEASE_READINESS.md with evidence links for every gate.

GATE 8 = "READY TO PUBLISH" (as a research + paper-trading platform): gates 1-8 green,
smoke green 7 days in a row, no open high/critical security findings.

## PHASE 9 — Live trading (ONLY after gates 7 and 8 AND my written approval in chat)
- [ ] docs/LIVE_TRADING_DESIGN.md first: my broker's API under SEBI's retail algo framework
    (broker-registered algo, algo ID on every order, static IP), manual-approve mode before any
    automatic mode, tiny hard capital caps, per-order and daily loss limits enforced server-side,
    kill switch, reconciliation with broker positions, full audit.
- [ ] The stage-2 safety guard changes only here, with my approval, replaced by tests that enforce the caps.

GATE 9: 4 weeks in manual-approve mode with tiny size, 100% reconciliation, my sign-off.
