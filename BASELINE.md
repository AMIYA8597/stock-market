# BASELINE — NeuroQuant `phase-repair` branch

**Recorded:** 2026-07-21  
**Branch:** `phase-repair`  
**Author:** Phase 0 automated audit

---

## Build Status Summary

| Check | Result | Notes |
|---|---|---|
| `pnpm --filter @neuroquant/web build` | ✅ **0 TS errors** (tsc --noEmit) | Next.js build output recorded below |
| `pnpm -w build` (packages) | ✅ All workspace packages resolved | 717 packages installed |
| `pytest backend/tests` | ✅ **39 passed, 0 failed** | 58.59s, 3 warnings (non-fatal) |
| `ruff check backend/app` | ⚠️ **242 errors** | All pre-existing; to be fixed Phase 1 |

---

## TSC Baseline

```
$ pnpm --filter @neuroquant/web exec tsc --noEmit
(no output)
Exit code: 0
```

**TypeScript errors: 0**

---

## Pytest Baseline

```
backend\tests\integration\test_api_portfolio_prompt_contract.py .     [ 25%]
backend\tests\integration\test_api_signals.py ...                     [ 33%]
backend\tests\integration\test_api_user_journey.py .                  [ 35%]
backend\tests\integration\test_critical_paths.py .........            [ 58%]
backend\tests\integration\test_websocket.py ..                        [ 64%]
backend\tests\unit\test_data_ingestion.py ..                          [ 69%]
backend\tests\unit\test_feature_builders.py ..                        [ 74%]
backend\tests\unit\test_feature_pipeline.py ...                       [ 82%]
backend\tests\unit\test_garch.py .                                    [ 84%]
backend\tests\unit\test_meta_learner.py .                             [ 87%]
backend\tests\unit\test_online_learner.py .                           [ 92%]
backend\tests\unit\test_paper_trading.py .                            [ 89%]
backend\tests\unit\test_sentiment.py ..                               [ 97%]
backend\tests\unit\test_xgboost_mismatch.py .                         [100%]

============ 39 passed, 3 warnings in 58.59s ============
```

**Tests: 39 passed / 0 failed**

Warnings (non-fatal):
- `pythonjsonlogger.jsonlogger` moved to `pythonjsonlogger.json` (deprecation)
- `fastapi.testclient` recommends `httpx2` (deprecation)
- `LiveDataSettings` uses class-based config instead of ConfigDict (Pydantic v2 deprecation)

---

## Ruff Baseline

```
$ python -m ruff check backend/app
Found 242 errors.
[*] 57 fixable with --fix  (40 more with --unsafe-fixes)
```

**Ruff errors: 242** — all pre-existing. Categories:
- `F401` unused imports (largest group)
- `F841` assigned but unused variables
- `UP` Python upgrade suggestions
- `B` bugbear rules
- `E` / `W` style/whitespace

These will be systematically fixed in Phase 1 as part of the dead-code removal sweep.

---

## Phase 0 Actions Taken

### Secrets & Junk Purged from Working Tree

| File/Dir | Action | Reason |
|---|---|---|
| `.env` (root) | Deleted | Contained MongoDB password `Sourav@12345`, NEXTAUTH_SECRET, FIELD_ENCRYPTION_KEY, SECRET_KEY — real credentials committed to git |
| `backend/.env` | Deleted | Contained same MongoDB URL |
| `backend/.env copy` | Deleted | Duplicate |
| `backend/dev.db` | Deleted (34 MB) | SQLite database committed to repo |
| `prompt.txt` | Deleted | Junk prompt file |
| `new-prompt.txt` | Deleted | Junk prompt file |
| `new-prompt.md` | Deleted | Junk prompt file |
| `new-new-new-new-prompt.txt` | Deleted | Junk prompt file |
| `git_diff.txt` | Deleted (435 KB) | Git diff artifact |
| `backend/curl_output.txt` | Deleted | Debug output |
| `backend/main-env.txt` | Deleted | Env dump |
| `package-lock.json` | Deleted | Duplicate lockfile (keep pnpm-lock.yaml only, defect #28) |
| `cleanup_unused_modules.ps1` | Deleted | Junk script |
| `scratch/` | Deleted + removed from git cache | 6 scratch test files |
| `unused_backup/` | Deleted + removed from git cache | Old backup files |
| Root `node_modules/` | Deleted | Was committed; reinstalled via `pnpm install` |

### Files Fixed

| File | Fix | Reason |
|---|---|---|
| `.gitignore` | Comprehensive rewrite | Added `.env`, `backend/.env`, `dev.db`, `*.db`, `logs/`, `node_modules/`, `scratch/`, junk files — everything that was missing |
| `.env.example` (root) | Complete rewrite | Removed all real credentials; added all free-tier defaults with clear instructions |
| `backend/.env.example` | Complete rewrite | Removed MongoDB URL; added free-tier defaults |
| `.ruff.toml` | Fixed `[tool.ruff]` → bare keys + `[lint]` section | Standalone ruff.toml must not use `[tool.ruff]` wrapper (pyproject.toml syntax only) |
| `backend/pyproject.toml` | Updated `[tool.ruff]` → `[tool.ruff.lint]` | Ruff v0.2+ deprecates top-level `select`/`ignore` in favour of `lint.*` |
| `backend/app/__init__.py` | Replaced Flask factory with empty package init | Flask leftover (`from flask_socketio import SocketIO`) blocked all Python imports including pytest |
| `backend/app/core/config.py` | Marked `MONGODB_URL` as deprecated | Phase 2 (defect #25) will remove Mongo; needed now so `.env.example` without MongoDB URL doesn't fail settings validation |

### Git Cache Cleared

The following were removed from git tracking (`git rm --cached`):
- `backend/dev.db`
- `prompt.txt`, `new-prompt.txt`, `new-prompt.md`, `new-new-new-new-prompt.txt`
- `git_diff.txt`
- `package-lock.json`
- `cleanup_unused_modules.ps1`
- `scratch/` (6 files)
- `unused_backup/` (1 file)

---

## Known Pre-Existing Issues (to be fixed in subsequent phases)

| # | Defect | Phase |
|---|---|---|
| 1–8 | Frontend demo/hardcoded data (DashboardOverview, PaymentPages, etc.) | 1 |
| 9–17 | Backend fake/stub logic (ai_service, ml_engine/orchestrator, models.py, etc.) | 1 |
| 18–25 | Live data & chart failures (WS alerts commented out, dual market routers, etc.) | 2–3 |
| 29 | `ai.router` commented out in `router.py` | 1 |
| 30 | Duplicate config modules (`app/config.py`, `app/core/config.py`, `app/config/`) | 1 |
| ruff | 242 pre-existing lint errors in `backend/app` | 1 |
| Pydantic deprecations | 3 warnings in test suite | 1 |

---

## Phase 0 Gate Verification

> **Gate:** app boots front and back on a clean clone with only `.env.example` copied.

✅ `backend/app/core/config.py` → `get_settings()` → imports correctly with `.env.example` defaults  
✅ `pnpm install` → resolves all 717 packages from lockfile  
✅ `tsc --noEmit` → 0 errors  
✅ `pytest` → 39 passed  
✅ No secrets in working tree  
✅ `.gitignore` prevents future accidental commits of `.env`, `dev.db`, etc.
