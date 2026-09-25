# Provider Matrix

| Provider | Data Domains | Regions | Status |
|---|---|---|---|
| yfinance | Quotes, OHLCV | Global | Active (Primary) |
| NSE (via raw HTTP) | Quotes, Universe | India | Secondary |
| Stooq | Quotes, OHLCV | Global | Secondary |

- **YFinance**: Primary for historical data. Implemented directly via `yfinance` python library to circumvent cookie/crumb scraping issues natively.
- **Stooq / NSE**: Configured as failovers.
