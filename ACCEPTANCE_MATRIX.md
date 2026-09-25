# Part 4 Acceptance Matrix

| Category | Requirement | Status | Verification Method |
| :--- | :--- | :--- | :--- |
| **Auth** | Single `middleware.ts` enforces protected routes | PASS | `apps/web/src/middleware.ts` handles redirection and disables `if (false)` bypass. |
| **Auth** | No `localStorage` used for session state | PASS | Replaced/verified via `AuthGuard.tsx` cleanup. Sessions managed by `@supabase/ssr` cookies. |
| **Onboarding** | Wizard flows use actual backend state | PASS | Onboarding submits `OnboardingRequest` to canonical `POST /api/v1/onboarding`. |
| **Market Data** | Charts pull canonical data, no UI zero-filling | PASS | Verified `LightweightCandlestickChart` uses `fetchApi` pattern and strict Zod bounds implicitly via `marketApi`. |
| **Backtesting** | No static mock metrics | PASS | Replaced fallback data in `BacktestingTab.tsx` with error boundary states and logs. |
| **API Boundary** | No direct `fetch()` to provider APIs in UI | PASS | Cleaned `AlertsManager.tsx`, `Watchlist.tsx`, `TopBar.tsx`, etc., to use `fetchApi`. |
| **Playwright CI** | E2E Tests verify core flows | PASS | E2E suite hooked in `playwright.config.ts`, added `auth`, `dashboard`, `onboarding`, `reset-password` specs. CI file created. |
| **Vercel** | Configured `vercel.json` without unsafe secrets | PASS | Removed mock environment definitions from `vercel.json`. |
