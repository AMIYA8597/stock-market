# NeuroQuant Operations Runbook

## 1. Incident Severity & Response Flow

```text
[Incident Detected] -> [1. Check Health & Readiness] -> [2. Identify Affected Layer] -> [3. Execute Runbook SOP]
```

### Fast Health Check Commands
```bash
# Public Health
curl -s https://neuroquant-api-6g57r5groa-el.a.run.app/health | jq .

# API & Dependency Status
curl -s https://neuroquant-api-6g57r5groa-el.a.run.app/api/v1/health | jq .

# Live Data Provider Feed Status
curl -s https://neuroquant-api-6g57r5groa-el.a.run.app/api/v1/health/live-data | jq .
```

---

## 2. Standard Operating Procedures (SOP)

### SOP-01: HTTP 500 / 502 / 503 Internal Server Error
1. **Diagnosis**:
   - Inspect Google Cloud Run logs:
     ```bash
     gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --project=tradebit-396406 --limit=50
     ```
   - Check if database connection pool is exhausted or pgBouncer is rejecting connections.
2. **Mitigation**:
   - Verify `DATABASE_URL` uses the transaction pooler (`aws-0-ap-northeast-1.pooler.supabase.com:6543`) rather than the session direct port (`5432`).
   - If a new revision deployed with broken migrations, rollback using Cloud Run revision traffic split:
     ```bash
     gcloud run services update-traffic neuroquant-api --to-revisions=PREVIOUS_REVISION=100 --region=asia-south1 --project=tradebit-396406
     ```

### SOP-02: HTTP 429 Too Many Requests
1. **Diagnosis**:
   - Check which endpoint is returning 429 (`/api/v1/market/quote` or Upstox upstream).
   - Ensure clients are using the batch endpoint: `GET /api/v1/market/quotes?symbols=...`.
2. **Mitigation**:
   - The in-memory / Redis token bucket allows 300 requests per 60 seconds per IP for authenticated routes.
   - If Upstox returns 429, check upstream quota consumption and ensure the 10-second quote cache is active.

### SOP-03: Upstox Token Expiration & Re-authentication
Upstox access tokens expire daily.
1. **Automated Refresh**:
   - A scheduled task or broker login flow exchanges the authorization code for a new bearer token.
2. **Manual Token Injection**:
   - Generate a valid token via Upstox Developer Portal.
   - Update Google Cloud Secret Manager:
     ```bash
     echo -n "NEW_UPSTOX_TOKEN" | gcloud secrets versions add UPSTOX_ANALYTICS_TOKEN --data-file=- --project=tradebit-396406
     ```
   - Redeploy or restart Cloud Run instances to pick up the updated secret.

### SOP-04: WebSocket Connection Failures & Reconnection Storms
1. **Diagnosis**:
   - Check client console for `WebSocket connection to 'wss://...' failed`.
   - Verify the client requests a ticket via `POST /api/v1/auth/ws-ticket` before connecting.
   - Check if Redis ticket key `ws:ticket:{ticket_id}` exists or HMAC signature matches.
2. **Mitigation**:
   - Verify `NEXT_PUBLIC_WS_URL` is set to `wss://neuroquant-api-6g57r5groa-el.a.run.app/ws/stream`.
   - Cloud Run service settings must include `--session-affinity` and `--timeout=3600s` to support long-lived WebSockets.

### SOP-05: Paper Trading & Emergency Kill Switch
1. **Verification**:
   - Verify `TRADING_MODE=paper` and `LIVE_ORDER_EXECUTION_ENABLED=false` are set.
2. **Emergency Kill Switch**:
   - To immediately stop all automated order generation:
     - Set `AUTOTRADE_ENABLED=false` in environment variables.
     - Call administrative kill switch endpoint `POST /api/v1/autotrade/kill-switch` with admin token.
   - All open simulated positions will be marked closed and background execution tasks halted.

---

## 3. Rollback Procedures

### Frontend (Vercel)
1. Open Vercel Project Dashboard (`https://vercel.com/neuroquant-sm`).
2. Navigate to **Deployments**.
3. Locate the previous stable production deployment and click **Instant Rollback**.

### Backend (Google Cloud Run)
1. List available revisions:
   ```bash
   gcloud run revisions list --service=neuroquant-api --region=asia-south1 --project=tradebit-396406
   ```
2. Route 100% of traffic to the desired revision:
   ```bash
   gcloud run services update-traffic neuroquant-api --to-revisions=neuroquant-api-PREVIOUS_ID=100 --region=asia-south1 --project=tradebit-396406
   ```
3. Verify `/health` on the restored revision.
