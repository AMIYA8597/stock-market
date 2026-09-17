# Security Audit

## Status
- `bandit` scanning passed for critical Python vulnerabilities.
- Known vulnerabilities check using `npm audit` or `pnpm audit` shows some warnings typical in large JS ecosystems, but no critical zero-days affecting runtime.

## Issues Identified
- Missing `.env` validation for critical production keys (OpenAI, Broker APIs).
- Cross-Site Request Forgery (CSRF) protection is present but needs strict validation on WebSockets to ensure hijacked sessions cannot subscribe to restricted data streams.

## Recommendations
- Implement strict JWT validation at the WebSocket connection level (in `app.core.websocket_manager`).
- Vault integration for storing Broker API keys (Zerodha/Upstox).
