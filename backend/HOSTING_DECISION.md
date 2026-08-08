# WebSocket Hosting Strategy & PaaS Decision

## Context
NeuroQuant relies heavily on an always-on backend to perform three critical continuous functions:
1. **Background Job Execution**: Running the `price_ticker.py` which continually fetches from yfinance/NSE and publishes to the internal pub/sub loop.
2. **WebSocket Broadcasting**: Maintaining long-lived TCP connections with active frontend clients for high-frequency pricing and regime signals.
3. **Alert Polling**: Checking and evaluating the rule-engine over continuous streaming data.

Traditional "serverless" or request-driven platforms (like Vercel, AWS Lambda, or standard Heroku Web Dynos with short timeouts) aggressively sever idle connections or restrict background threads. AWS AppRunner terminates connections after 100 seconds of inactivity. We need a provider that treats long-running containerized background workers and persistent TCP connections as a first-class citizen.

## Options Evaluated
1. **Render (Web Service)**: Supports WebSockets natively. However, on the free tier, services sleep after 15 minutes of inactivity, tearing down WebSockets. A paid $7/mo plan works well but is known to drop long-lived connections during aggressive autoscaling or deploy swaps.
2. **Fly.io**: Purpose-built for edge connectivity. Natively routes long-lived WebSockets cleanly via Anycast IP. Allows `fly.toml` to define both a web process (uvicorn) and a background worker process (celery/scheduler) seamlessly. Billed on active RAM usage, easily fitting under $5/mo for basic persistent workloads.
3. **Railway.app**: Excellent Developer Experience (DX) and supports persistent connections natively. Billed per minute (roughly $5/mo). Does not force connection resets and handles Python async/WebSocket traffic beautifully.

## Decision
**Fly.io** is selected as the primary hosting provider for the backend API and worker processes. 

## Rationale
Fly.io provides:
1. **Uninterrupted TCP/WebSockets**: Unlike AppRunner or Vercel, Fly's edge proxies (`fly-proxy`) are explicitly designed to maintain long-lived WebSocket connections. 
2. **Graceful degradation capability**: Under extreme loads, Fly's internal load balancers queue and throttle requests natively before they hit the Python event loop.
3. **Internal networking (IPv6)**: We can seamlessly host an internal Redis instance (for pub/sub and signals) not exposed to the public internet without paying for an expensive managed cloud Redis tier. 
4. **Predictable Scaling**: Adding a second worker for the `price_ticker` if the symbol list expands past 500 is a single CLI command (`fly scale count 2`).

## Execution Constraints
- Ensure `fly.toml` explicitly configures `[http_service.concurrency]` to a high `hard_limit` (e.g., 500) to ensure the proxy doesn't prematurely drop WebSocket clients under moderate concurrency. 
- Implement Redis locally inside the Fly private network for the pubsub, using the `flyctl redis create` extension or deploying the `redis:alpine` docker image alongside the app.
