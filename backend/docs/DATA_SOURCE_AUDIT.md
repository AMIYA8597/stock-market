# Data Source Audit & Priority

## Overview
This document outlines the data source hierarchy used by the **MarketDataService** for fetching live quotes and historical OHLCV data.

### Live Quote (`get_quote`)
1. **Upstox** – Real‑time NSE feed (if configured and token available).
2. **Yahoo Finance (yfinance)** – Free delayed quote.
3. **Stooq** – Not applicable for live quote (Stooq only provides daily OHLCV).

### Historical Data (`get_history` / `get_intraday_candles`)
1. **Upstox** – Currently not a historical source; placeholder for future implementation.
2. **Yahoo Finance (yfinance)** – Primary free source.
3. **Stooq** – Daily OHLCV fallback when Yahoo Finance fails or for NSE symbols where daily granularity is sufficient.

## Source Selection Logic
- The **DataIngestionOrchestrator** selects sources based on asset type and symbol suffixes. For NSE equities (`*.NS`), it tries **NSESource**, then **yfinance**, then **Stooq**.
- The service caches the chosen source in the returned `HistoryList.source` attribute for downstream components.

## Auditing
- Each fetch logs the selected source to facilitate monitoring and debugging.
- Live quote responses include a `source` field indicating the origin (`"upstox"` or `"yfinance"`).

## Future Enhancements
- Integrate Upstox as a historical source when an API endpoint becomes available.
- Add configurable priority overrides via environment variables.
