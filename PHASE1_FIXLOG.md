# Phase 1: Mock Data Eradication Log

The objective of Phase 1 was to purge all traces of mock, demo, and hardcoded arrays across the application to ensure that the UI renders real walk-forward data accurately from the backend, failing gracefully (or showing an honest empty state) when data is unavailable.

## Purged Files and Paths

### 1. `apps/web/src/modules/dashboard/DashboardOverview.tsx`
- **Removed**: `hardcodedMockData` object array.
- **Removed**: `seedPortfolioPerformance` hardcoded dataset.
- **Removed**: `demoTrades` list.
- **Replaced**: Hardcoded `regimeScores` and regime bar percentages with dynamic responses from `signalsApi`.
- **Replaced**: `modelWeights` mock object mapped to real signal engine metadata (`signal.model_weights`).

### 2. `apps/web/src/modules/admin/AdminPanelPage.tsx`
- **Removed**: `seedUsers` hardcoded array.
- **Removed**: `seedContentRows` mock list.
- **Replaced with**: Real backend queries fetching from the unified admin endpoint layer (`adminApi`).

### 3. `apps/web/src/modules/blog/BlogPages.tsx`
- **Removed**: `seedPosts` mock blog posts array.
- **Removed**: Hardcoded demonstration text inside `BlogArticlePage` that artificially simulated a post.

### 4. `apps/web/src/modules/notifications/NotificationCenterPage.tsx`
- **Removed**: `seedRows` mock notification array.
- **Replaced with**: Live backend polling setup using `notificationsApi.list()`.

### 5. `apps/web/src/modules/public/LandingPage.tsx`
- **Removed**: `marketCards` and `testimonials` mock data structures used for the premium marketing demo.

### 6. `backend/app/api/v1/signals.py` & Backend (Earlier Fixes)
- **Removed**: Mock optimization results and hardcoded symbol lists.
- **Replaced with**: Dynamic fetching from FastAPI. 

## Next Steps (Phase 2 & Beyond)
- One canonical data layer for state management across components.
- Live WebSockets for real-time telemetry updates.
- ML Backtesting integration and advanced visualization integration.
