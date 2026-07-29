# QuantEdge — Knowledge Transfer Documentation

## Project Overview

QuantEdge is an AI-powered stock market intelligence system with a FastAPI backend and a Next.js frontend. It provides real-time signal feeds, portfolio management, market data, predictions, and watchlist functionality.

**Tech Stack:**
- Backend: Python 3.11+, FastAPI, SQLAlchemy (async), Redis, PostgreSQL
- Frontend: Next.js 14.2.15, React 18.3.1, TypeScript, Zustand, Recharts
- WebSocket: FastAPI WebSocket for live signal/price feeds

---

## Architecture

### Backend (`backend/`)
- `app/main.py` — FastAPI entry point, CORS config, router mounting
- `app/core/config.py` — Settings (DATABASE_URL, CORS origins, etc.)
- `app/core/dependencies.py` — Shared dependencies (get_db, get_redis, get_current_user, etc.)
- `app/core/errors.py` — Exception handlers (validation, HTTP, generic)
- `app/core/middleware.py` — SecurityHeadersMiddleware, RateLimitMiddleware
- `app/api/v1/` — API routers (watchlist, portfolio, market, predictions, etc.)
- `app/infrastructure/market_data/router.py` — Market data endpoints with Redis caching
- `app/websocket/` — WebSocket endpoints for live signals and prices
- `app/database/` — SQLAlchemy engine, session factory, Redis client

### Frontend (`apps/web/`)
- `src/lib/api-client.ts` — Main API client with auth token injection, retry logic
- `src/lib/contracts-api.ts` — Legacy contracts API (used by dashboard/components)
- `src/lib/runtime-config.ts` — API/WS base URL configuration
- `src/stores/authStore.ts` — Zustand auth state management
- `src/hooks/useSignalFeed.ts` — WebSocket signal feed hook
- `src/hooks/useSignalAlerts.ts` — WebSocket alerts hook
- `src/hooks/usePriceFeed.ts` — Price feed hook
- `src/components/auth/AuthGuard.tsx` — Route protection
- `src/components/terminal/Watchlist.tsx` — Watchlist with 4 custom lists + Market tab

---

## Key Fixes Applied

### 1. Watchlist Duplicate Keys (High Priority)
**File:** `apps/web/src/components/terminal/Watchlist.tsx`
**Issue:** `TCS.NS` appeared twice in watchlist list 0, causing React duplicate key warnings (`0-TCS.NS`).
**Fix:** Removed the duplicate `TCS.NS` entry from line 138.

### 2. WebSocket Cleanup on Unmount (High Priority)
**Files:** `apps/web/src/hooks/useSignalFeed.ts`, `apps/web/src/hooks/useSignalAlerts.ts`
**Issue:** When components unmounted, the WebSocket `onclose` handler triggered a reconnect attempt, causing "WebSocket is closed before the connection is established" errors and state updates on unmounted components.
**Fix:** Added a `mountedRef` boolean ref to both hooks. The `onclose` handler now checks `mountedRef.current` before reconnecting. The cleanup effect sets `mountedRef.current = false` before closing the WebSocket.

### 3. AuthGuard Redirect Loop (High Priority)
**File:** `apps/web/src/stores/authStore.ts`
**Issue:** When `fetchProfile()` failed (e.g., server error 500), it cleared tokens and set `isAuthenticated: false`, causing AuthGuard to redirect to login. Login sets tokens again, fetchProfile fails again → infinite redirect loop.
**Fix:** Changed `fetchProfile()` to only clear tokens on 401 (Unauthorized) errors. For other errors (500, network), it keeps the tokens and shows an error message instead of redirecting.

### 4. Missing Auth Tokens in contracts-api.ts (High Priority)
**File:** `apps/web/src/lib/contracts-api.ts`
**Issue:** The `getJson()` and `postJson()` functions did not include `Authorization` headers, causing 400/401 errors on authenticated endpoints like `/portfolio/holdings`.
**Fix:** Added `getAccessToken()` helper that reads `nq_access_token` from localStorage. Both `getJson()` and `postJson()` now include the `Authorization: Bearer <token>` header when a token is present.

### 5. CORS Headers Missing on Error Responses (Medium Priority)
**File:** `backend/app/core/errors.py`
**Issue:** When the backend returned unhandled exceptions (500 errors), the response didn't go through the CORS middleware properly, causing CORS policy errors in the browser.
**Fix:** Added a `generic_exception_handler` that catches all unhandled exceptions and returns a proper JSON response. Registered it with `app.add_exception_handler(Exception, generic_exception_handler)`.

### 6. Chart ResponsiveContainer Sizing Warnings (Medium Priority)
**File:** `apps/web/src/modules/dashboard/DashboardOverview.tsx`
**Issue:** `ResponsiveContainer` with `width="100%" height="100%"` rendered with 0 dimensions because the parent container used `min-h-[320px]` (minimum height) instead of an explicit height.
**Fix:** Changed `min-h-[320px]` to `h-[320px]` on the parent div so the ResponsiveContainer has a defined height to work with.

### 7. Redis 503 Errors on Market Data Endpoints (Medium Priority)
**Files:** `backend/app/core/dependencies.py`, `backend/app/infrastructure/market_data/router.py`
**Issue:** The `get_redis` dependency raised HTTP 503 when Redis was unavailable, making all market data endpoints (quote, WebSocket quotes) return 503 errors.
**Fix:** Created `get_redis_optional` dependency that returns `None` instead of raising 503 when Redis is unavailable. Updated the market data router to use `get_redis_optional` and gracefully handle `redis=None` (skip caching, fetch directly from provider).

---

## Auth Flow

1. User logs in → `authApi.login()` → tokens stored in localStorage via `setAuthTokens()`
2. `setTokens()` sets `isAuthenticated: true` and calls `fetchProfile()`
3. `fetchProfile()` calls `authApi.getProfile()` (`/auth/me`) to get user details
4. On success: `user` is set, `isAuthenticated: true`, `isLoading: false`
5. On 401 error: tokens cleared, `isAuthenticated: false`, redirect to login
6. On other errors (500, network): tokens kept, error message shown, user stays on page
7. AuthGuard checks `!isLoading && !isAuthenticated` → redirects to login if not authenticated

## API Client Architecture

- `api-client.ts`: Primary API client with auth token injection, auto-refresh on 401, retry on 5xx
- `contracts-api.ts`: Legacy contracts API used by dashboard components — now includes auth tokens
- `runtime-config.ts`: Centralized URL configuration (`NEXT_PUBLIC_API_URL` env var)

## WebSocket Architecture

- `useSignalFeed.ts`: Subscribes to `/ws/signals` for live signal updates
- `useSignalAlerts.ts`: Subscribes to `/ws/alerts` for signal alert notifications
- Both hooks implement reconnect with exponential backoff (max 30s)
- Both hooks properly clean up on unmount (close WS, clear reconnect timers)

## CORS Configuration

- Configured in `backend/app/core/config.py` via `BACKEND_CORS_ORIGINS`
- Applied via `CORSMiddleware` in `backend/app/main.py`
- Also handled by `SecurityHeadersMiddleware` for rate-limited responses
- Generic exception handler ensures CORS headers on all error responses

## Redis Caching

- Redis is used for caching market data quotes and signal data
- `get_redis()` — hard dependency (returns 503 if Redis unavailable)
- `get_redis_optional()` — soft dependency (returns None if Redis unavailable)
- Market data endpoints use `get_redis_optional` for graceful degradation

---

## Running the Project

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:create_app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd apps/web
npm install
npm run dev
```

### Environment Variables
- `NEXT_PUBLIC_API_URL`: Frontend API base URL (default: `http://localhost:8000`)
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string (optional — caching degrades gracefully)
- `BACKEND_CORS_ORIGINS`: Comma-separated list of allowed CORS origins

---

## Testing

Run backend tests:
```bash
cd backend
pytest tests/ -v
```

Run frontend tests:
```bash
cd apps/web
npm test
```
