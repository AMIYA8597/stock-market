#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# PRODUCTION DEPLOYMENT CHECKLIST
# Stock Market AI Trading Intelligence Platform
# Version: 1.0  |  Date: March 29, 2026
# ═══════════════════════════════════════════════════════════════════════════════

echo "╔════════════════════════════════════════════════════════════════════════════════╗"
echo "║                  🚀 PRODUCTION DEPLOYMENT CHECKLIST 🚀                         ║"
echo "║              Stock Market AI Trading Intelligence Platform                    ║"
echo "╚════════════════════════════════════════════════════════════════════════════════╝"
echo ""

# ─────────────────────────────────────────────────────────────────────────────────
# PRE-DEPLOYMENT (Run in staging environment)
# ─────────────────────────────────────────────────────────────────────────────────

echo "📋 PRE-DEPLOYMENT CHECKLIST"
echo "══════════════════════════════════════════════════════════════════════════════"
echo ""

declare -a PreDeploymentTasks=(
  "☐ Review FINAL_PRODUCTION_SCORECARD.md (82/100 ready for production)"
  "☐ Verify all 10 CRITICAL security fixes are committed"
  "☐ Confirm new-prompt.txt requirements are 100% implemented"
  "☐ Check git log for production-readiness commit"
  "☐ Review PHASE2_IMPLEMENTATION_REPORT.md for completeness"
)

for task in "${PreDeploymentTasks[@]}"; do
  echo "$task"
done

echo ""
echo "📊 STAGING ENVIRONMENT VERIFICATION"
echo "══════════════════════════════════════════════════════════════════════════════"
echo ""

cat << 'EOF'

1️⃣  DATABASE MIGRATION
  ────────────────────────────────────────────────────────────────────────────
  
  [ ] SSH into staging database server
  
  [ ] Run migration:
      cd /opt/app/backend
      alembic upgrade head
  
  [ ] Verify CSRF table created:
      psql $(DATABASE_URL) -c "\dt csrf_tokens"
      Expected output: Table "public.csrf_tokens"
  
  [ ] Verify 17 new indexes exist:
      psql $(DATABASE_URL) -c "\d+ users" | grep "email"
      psql $(DATABASE_URL) -c "\d+ payment_transactions" | grep "intent_id"
      psql $(DATABASE_URL) -c "\d+ csrf_tokens" | grep "user_id"
  
  [ ] Rollback plan ready:
      alembic downgrade -1
      (Removes CSRF table, drops all new indexes)
  
  [ ] Database backup taken:
      pg_dump $(DATABASE_URL) | gzip > /backups/pre-deploy-$(date +%Y%m%d).sql.gz

2️⃣  ENVIRONMENT VARIABLE CONFIGURATION
  ────────────────────────────────────────────────────────────────────────────
  
  [ ] REQUIRED: Set Sentry DSN (production secret stored in AWS Secrets Manager)
      export SENTRY_DSN="https://[key]@sentry.io/[project-id]"
  
  [ ] REQUIRED: Set Stripe webhook secret (production secret, not test)
      export STRIPE_WEBHOOK_SECRET="whsec_live_..."
  
  [ ] REQUIRED: Set JWT RS256 keys (production keys generated & rotated)
      export JWT_PRIVATE_KEY=$(cat /secrets/jwt_private_key)
      export JWT_PUBLIC_KEY=$(cat /secrets/jwt_public_key)
  
  [ ] OPTIONAL: Configure ELK/Datadog for structured logging
      export LOG_DESTINATION="datadog://[api-key]@logs.datadoghq.com"
  
  [ ] OPTIONAL: Configure AlertManager for critical errors
      export ALERTMANAGER_URL="https://alertmanager.staging.example.com"
  
  Verification:
      env | grep "SENTRY\|STRIPE\|JWT" (check secrets are set, values not visible)

3️⃣  SMOKE TESTS (Manual testing on staging)
  ────────────────────────────────────────────────────────────────────────────
  
  USER REGISTRATION & AUTH
  [ ] Register new user → receives email confirmation (or console log in test)
  [ ] Attempt login with wrong password 5x → account locked
  [ ] Wait 15 minutes → account unlocks (or force-unlock in admin)
  [ ] Login with correct password → JWT tokens issued
  [ ] Use refresh token → new access token issued
  [ ] Logout → refresh token invalidated
  
  PORTFOLIO & MARKETS
  [ ] View markets page → loads in < 2 seconds
  [ ] Add stock to watchlist → persists to database
  [ ] Place simulated trade → portfolio value updates
  [ ] Set price alert → receives email notification on trigger
  
  PAYMENTS (TEST MODE)
  [ ] Navigate to billing → create payment intent (Stripe test card: 4242 4242...)
  [ ] Submit payment → transaction recorded with unique intent_id
  [ ] Submit SAME request twice with same Idempotency-Key → should return same result
  [ ] Inject webhook event manually (stripe event fixture) → transaction status updates
  [ ] Webhook event replayed (same provider_event_id) → no duplicate transaction
  
  ERROR HANDLING
  [ ] Trigger validation error → response includes error_code (string) + message
  [ ] Trigger 404 → includes request_id in response
  [ ] Trigger rate limit (10+ auth attempts) → 429 with retry-after header
  [ ] View logs → JSON structured format with request_id, user_id, email fields

4️⃣  LOAD TESTING (Using k6 or Apache JMeter)
  ────────────────────────────────────────────────────────────────────────────
  
  TARGET METRICS:
  ├─ Response time p95: < 200ms (target)
  ├─ Error rate: < 0.5%
  ├─ Throughput: > 100 req/sec
  └─ Database connections: < 15/20 max
  
  LOAD TEST COMMANDS:
  
  $ k6 run --vus 50 --duration 5m \
      scripts/load-test-baseline.js
  
  EXPECTED RESULTS:
  ├─ Registration endpoint: 100 req/s average
  ├─ Login endpoint: 150 req/s average (auth is fast with caching)
  ├─ Market data endpoint: 500 req/s average (read-only, heavily cached)
  ├─ Payment endpoint: 20 req/s (heavier computation, Stripe API calls)
  └─ No errors, p95 latency < 300ms
  
  [ ] Load test passed with acceptable metrics
  [ ] Database connection pool not exhausted during test
  [ ] No memory leaks detected (check resident memory stable)

5️⃣  SECURITY VERIFICATION
  ────────────────────────────────────────────────────────────────────────────
  
  [ ] Run OWASP ZAP or Burp Suite against staging environment
      Expected: 0 HIGH severity issues, ≤3 MEDIUM issues (acceptable)
  
  [ ] Verify security headers in response:
      curl -I https://staging.example.com/api/v1/health | grep -i "strict-transport-security"
      curl -I https://staging.example.com/api/v1/health | grep -i "content-security-policy"
  
  [ ] Check no secrets in logs:
      tail -100 /var/log/app.log | grep -i "password\|token\|secret\|key"
      (Should return ZERO matches)
  
  [ ] Verify JWT RS256 in use (not HS256):
      curl https://staging.example.com/api/v1/auth/login -X POST ... \
        | jq '.access_token' | jwt decode
      (Verify algorithm: RS256, not HS256)
  
  [ ] Account lockout working:
      1. Login wrong password 5 times
      2. Verify account locked (locked_until timestamp in DB)
      3. Attempt 6th login → 400 error "Account locked"
  
  [ ] Payment webhook signature verification working:
      Test with invalid signature → 401 Unauthorized
      Test with valid signature → 200 OK

6️⃣  INTEGRATION TEST SUITE
  ────────────────────────────────────────────────────────────────────────────
  
  [ ] Run full integration test suite:
      cd backend/
      pytest tests/integration/test_critical_paths.py -v
  
  [ ] Expected results:
      ├─ TestAuthFlow::test_register_login_refresh_logout ✅
      ├─ TestAuthFlow::test_account_lockout_after_failed_attempts ✅
      ├─ TestPaymentFlow::test_idempotency_prevents_duplicates ✅
      ├─ TestPaymentFlow::test_webhook_deduplication ✅
      ├─ TestErrorResponseFormat::test_all_endpoints_return_standard_format ✅
      ├─ TestRateLimiting::test_auth_endpoint_rate_limit ✅
      └─ TestDatabaseConstraints::test_indexes_exist ✅
  
  [ ] Coverage report generated:
      pytest tests/integration/test_critical_paths.py --cov=app --cov-report=html
      (Review coverage.html in browser)

7️⃣  INFRASTRUCTURE READINESS
  ────────────────────────────────────────────────────────────────────────────
  
  [ ] Load balancer configured for blue-green deployment
  [ ] Health check endpoint (/health, /ready) responding
  [ ] Docker image built and tested locally
  [ ] Container registry updated with latest image tag
  [ ] Kubernetes manifests updated (or ECS task definitions)
  [ ] Scaling policies configured (auto-scale at CPU > 70%)
  [ ] Log aggregation destination functional (Datadog/ELK)
  [ ] Error tracking (Sentry) dashboard accessible

EOF

echo ""
echo "🚀 PRODUCTION DEPLOYMENT EXECUTION"
echo "══════════════════════════════════════════════════════════════════════════════"
echo ""

cat << 'EOF'

DEPLOYMENT STRATEGY: Blue-Green Deployment (Zero Downtime)
────────────────────────────────────────────────────────────────────────────

1️⃣  PRE-DEPLOYMENT CHECKLIST
  ✓ All staging tests passed
  ✓ Performance metrics acceptable
  ✓ Security audit sign-off
  ✓ Rollback plan documented and tested

2️⃣  DEPLOYMENT WINDOW (2 AM UTC - Off-peak hours)
  
  Step 1: Deploy to GREEN environment (parallel to BLUE)
  ├─ Pull new Docker image from registry
  ├─ Run database migration (alembic upgrade head)
  ├─ Set environment variables (Sentry, Stripe, JWT keys)
  └─ Start container and wait for health checks to pass
  
  Step 2: Smoke test GREEN environment
  ├─ Quick auth flow test (register, login, refresh, logout)
  ├─ Verify error responses standardized
  └─ Confirm payment webhook working
  
  Step 3: Switch load balancer from BLUE → GREEN
  ├─ Update load balancer routing rules (30 second change)
  ├─ Monitor error rate for 30 seconds
  └─ Verify traffic successfully routing to GREEN
  
  Step 4: Monitor for 5 minutes
  ├─ Error rate < 0.5%
  ├─ Latency p95 < 200ms
  ├─ Database connections stable
  └─ No spike in Sentry errors
  
  Step 5: Keep BLUE running for 1 hour (rollback window)
  ├─ If any issues detected: switch back to BLUE
  ├─ After 1 hour stability: decommission BLUE

3️⃣  ROLLBACK PROCEDURE (If issues detected)
  
  IMMEDIATE ACTIONS (< 5 minutes):
  ├─ [T+0:00] Switch load balancer from GREEN → BLUE
  ├─ [T+0:30] Monitor error rate returns to < 0.5%
  ├─ [T+2:00] Verify traffic successfully on BLUE
  └─ [T+5:00] Page on-call engineer for investigation
  
  DATABASE ROLLBACK:
  └─ alembic downgrade -1
      (Removes CSRF table, drops 17 new indexes)
      WARNING: Takes ~30 seconds on large database
  
  CODE ROLLBACK:
  └─ git revert (push previous commit)
      No downtime during blue-green deployment

EOF

echo ""
echo "📊 POST-DEPLOYMENT MONITORING (First 24 hours)"
echo "══════════════════════════════════════════════════════════════════════════════"
echo ""

cat << 'EOF'

CRITICAL METRICS (check every 5 minutes for first hour)
────────────────────────────────────────────────────────────────────────────

[ ] Error Rate: < 0.5%
    └─ Watch for: 5xx errors, validation errors, database connection errors

[ ] Latency p95: < 200ms
    └─ Watch for: Slow queries, payment API calls timing out

[ ] Database Connections: < 15/20 max
    └─ Watch for: Connection pool exhaustion, queries holding locks

[ ] Request ID Coverage: 100%
    └─ Verify: Every response includes x-request-id header

[ ] Sentry Errors: < 5 errors/minute
    └─ Watch for: Account lockout issues, CSRF validation, payment webhooks

IMPORTANT METRICS (check every 30 minutes for first 4 hours)
────────────────────────────────────────────────────────────────────────────

[ ] Authentication Success Rate: > 99%
[ ] Payment Success Rate: > 99.5%
[ ] Email Queue Depth: < 100 (should be processing)
[ ] Cache Hit Rate: > 80% (indicates Redis is working)

OPTIONAL MONITORING (check during business hours)
────────────────────────────────────────────────────────────────────────────

[ ] UI Performance: Lighthouse score > 85
[ ] API Gateway Throughput: > 100 req/sec average
[ ] Database Replication Lag: < 100ms
[ ] Backup Completion: Daily backups successful

ALERT THRESHOLDS (Should trigger page/Slack if exceeded)
────────────────────────────────────────────────────────────────────────────

🔴 CRITICAL (Page on-call immediately):
  − Error rate > 5%
  − Latency p99 > 2 seconds
  − Database connection pool > 18/20
  − Payment webhook failures > 10/hour
  − 5xx errors for critical endpoints

🟡 WARNING (Slack alert, not page):
  − Error rate > 1%
  − Latency p95 > 500ms
  − Database connection pool > 15/20
  − Email queue depth > 1000
  − Cache hit rate < 60%

EOF

echo ""
echo "✅ DEPLOYMENT SIGN-OFF"
echo "══════════════════════════════════════════════════════════════════════════════"
echo ""

cat << 'EOF'

RESPONSIBLE PARTIES
────────────────────────────────────────────────────────────────────────────

Platform Engineer:      ________________________    Date: ___________
(Deploys to production)

DevOps Engineer:        ________________________    Date: ___________
(Verifies infrastructure readiness)

Security Engineer:      ________________________    Date: ___________
(Final security sign-off)

Engineering Manager:    ________________________    Date: ___________
(Deployment approval)

On-Call Engineer:       ________________________    Date: ___________
(Standing by for rollback)

DEPLOYMENT AUTHORIZATION

[ ] All checklist items completed
[ ] Staging environment tests passed
[ ] Security audit approved
[ ] Infrastructure readiness confirmed
[ ] Rollback procedure tested and ready
[ ] On-call team briefed and standing by

STATUS: ⏳ Ready for Production Deployment

DEPLOYMENT DATE: ________________
DEPLOYMENT TIME: ________________
ENVIRONMENT: Production
REVISION: ________________
NAMESPACE: trading (or custom namespace)

═══════════════════════════════════════════════════════════════════════════════
EOF

echo ""
echo "✅ DEPLOYMENT CHECKLIST COMPLETE"
echo ""
echo "Next step: Run deployment procedure (see section 🚀 PRODUCTION DEPLOYMENT)"
echo ""
