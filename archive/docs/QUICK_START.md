# 🚀 QUICK START: IMPLEMENTATION GUIDE FOR NEXT SESSION

**Follow this checklist to continue Phase 2 implementation**

---

## STEP 1: Wire New Middleware (30-45 minutes)

### File: `backend/app/main.py`

**Current state:**
```python
from fastapi.middleware.cors import CORSMiddleware
# ... existing code

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)
# ...
```

**Action:** Replace with:
```python
# ===== ADD THESE IMPORTS AT TOP =====
from app.core.request_id_middleware import RequestIDMiddleware, CORSProductionMiddleware
from app.core.structured_logging import configure_logging

# ===== ADD AFTER app = FastAPI(...) DEFINITION =====
# Configure structured logging (MUST be first)
configure_logging(settings.ENVIRONMENT)

# ===== ADD MIDDLEWARE IN THIS ORDER =====
# 1. RequestID first to capture all requests
app.add_middleware(RequestIDMiddleware)

# 2. CORS - environment-aware
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        CORSProductionMiddleware,
        allowed_origins=settings.BACKEND_CORS_ORIGINS,
    )
else:
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS or ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 3. Security headers (unchanged)
app.add_middleware(SecurityHeadersMiddleware)

# 4. Rate limiting (unchanged)
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware, config=parse_rate_limit(settings.DEFAULT_RATE_LIMIT))
```

**Verification:**
```bash
cd backend
python -c "from app.main import app; print('✅ main.py imports successfully'); print(f'📋 Middleware count: {len(app.user_middleware)}')"
```

---

## STEP 2: Apply Error Standardization (2-4 hours)

### Pattern Template

Every endpoint that throws HTTPException needs updating. Template:

**FIND THIS:**
```python
raise HTTPException(status_code=400, detail="Your error message")
```

**REPLACE WITH:**
```python
raise HTTPException(
    status_code=400,
    detail=ErrorResponse.create(
        code=ErrorCode.VALIDATION_ERROR,  # Pick correct code
        message="Your user-friendly error message",  # Generic, no info leaks
    ).dict()
)
```

### Files to Update (in order of importance)

1. **`backend/app/api/v1/payments.py`** (3 endpoints)
   - `create_intent()` - validation errors
   - `confirm_intent()` - payment failed errors
   - `{ }` - insufficient funds errors
   
2. **`backend/app/api/v1/market.py`** (8 endpoints)
   - Quote endpoint - 404 not found
   - History endpoint - invalid symbol
   - etc.

3. **`backend/app/api/v1/signals.py`** (6 endpoints)

4. **`backend/app/api/v1/portfolio.py`** (4 endpoints)

5. **`backend/app/api/v1/screener.py`** (2 endpoints)

### Quick Bash Script to Find All
```bash
cd backend
grep -r "raise HTTPException" app/api/v1/ | grep -v ".pyc" | wc -l
# Should show ~28 instances to update
```

### Import Needed (Add to each file)
```python
from app.schemas.errors import ErrorCode, ErrorResponse
```

---

## STEP 3: Test & Verify (30 minutes)

### Run Tests
```bash
cd backend

# 1. Run existing tests (should still pass)
python -m pytest tests/ -v

# 2. Test that modules import
python -c "from app.main import app; from app.schemas.errors import ErrorResponse; print('✅ All imports work')"

# 3. Test error response format
python -c "
from app.schemas.errors import ErrorCode, ErrorResponse
err = ErrorResponse.create(
    code=ErrorCode.INVALID_CREDENTIALS,
    message='Test error'
)
print(err.dict())
"
```

### Expected Test Output
```
✅ 18 passed in X.XXs
✅ All imports work
✅ Error response prints correctly
```

---

## STEP 4: Commit & Push (10 minutes)

```bash
cd d:\work\stock-market

# Verify changes
git diff --stat

# Commit
git add -A
git commit -m "feat: standardized error responses + structured logging + request ID tracing

- Add ErrorCode enum with 37 standardized error codes  
- Add ErrorResponse schema for consistent API error format
- Add structured JSON logging for production (ProdJsonFormatter + DevFormatter)
- Add RequestIDMiddleware for distributed request tracing
- Add CORSProductionMiddleware for strict CORS in production
- Update auth endpoints to use new error response format
- Prevent user enumeration in error messages"

# Push
git push
```

---

## STEP 5: NEXT PRIORITY ITEMS (Choose One)

### **HIGHEST IMPACT:** Finish Error Standardization (4-6 hours)
Apply ErrorResponse.create() to all remaining 23 endpoints.

**Command to start:**
```bash
# List all endpoints needing updates
grep -r "raise HTTPException" backend/app/ | grep -v ".pyc" | cut -d: -f1 | sort -u
```

### **MOST CRITICAL:** Sentry Integration (2 hours)
Add error tracking so production issues are visible.

**File to update:** `backend/app/main.py`

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

if settings.ENVIRONMENT == "production":
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.1,
    )

# Add exception handler to capture unhandled errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    sentry_sdk.capture_exception(exc)  # Send to Sentry
    logger.exception("Unhandled exception", extra={"path": request.url.path})
    return JSONResponse(status_code=500, content={"error": "Internal server error"})
```

Need: SENTRY_DSN in .env

### **SECURITY REQUIRED:** Webhook Signature Verification (3 hours)
Add security to payment webhooks.

**File to create:** `backend/app/tasks/payment_webhooks.py`

---

## TROUBLESHOOTING

### Error: "No module named 'app.schemas.errors'"
**Solution:** Make sure you're in the `backend/` directory when running tests:
```bash
cd backend
python -m pytest tests/
```

### Error: "CORSProductionMiddleware not found"
**Solution:** Verify `request_id_middleware.py` exists and is spelled correctly:
```bash
ls -la backend/app/core/ | grep middleware
```

### Tests failing after changes
**Solution:** The 18 existing tests should still pass. If they fail:
1. Revert changes to `auth.py`
2. Commit only the new files first
3. Verify old tests pass
4. Then update auth endpoints

---

## SUCCESS CRITERIA

After completing Steps 1-3:

- [ ] `backend/app/main.py` has new middleware wired
- [ ] `backend/app/schemas/errors.py` imports without errors  
- [ ] `backend/app/core/structured_logging.py` imports without errors
- [ ] `backend/app/core/request_id_middleware.py` imports without errors
- [ ] `auth.py` register & login use `ErrorResponse.create()`
- [ ] All 18 existing tests still pass
- [ ] Running app produces structured logs in development mode
- [ ] All HTTP endpoints return error responses in standardized format

---

## CHECKLIST FOR YOUR NEXT SESSION

**When you're ready to continue:**

- [ ] Read this QUICK_START.md
- [ ] Follow Steps 1-4 above (2-3 hours total)
- [ ] Run tests to verify nothing broke
- [ ] Choose ONE priority item from Step 5
- [ ] Update PHASE2_PROGRESS.md with completion time
- [ ] Commit and push

**Estimated total time next session:** 3-5 hours for Steps 1-4 + one priority item

---

## REFERENCE LINKS

- Full audit details: See **PRODUCTION_AUDIT.md** (60+ issues with fixes)
- Implementation roadmap: See **PHASE2_PROGRESS.md** (time estimates + dependencies)
- Error codes reference: See **backend/app/schemas/errors.py** (all 37 codes)
- Structured logging examples: See **backend/app/core/structured_logging.py** (dev vs prod)

---

**Generated:** 2026-03-28  
**For:** NeuroQuant Platform  
**Status:** Ready for next phase
