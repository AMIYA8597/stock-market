# DEMO_SCRIPT.md

## Prerequisites
- Backend services running locally on `localhost:8000`
- Frontend running locally on `localhost:3000`

## Flow 1: Authentication & Onboarding
1. Navigate to `http://localhost:3000/en/login`
2. Attempt to login with invalid credentials to demonstrate error states.
3. Click "Register" and create a new account.
4. You will be redirected to the Onboarding wizard.
5. Complete the 4-step wizard:
   - **Profile**: Set name and timezone.
   - **Organization**: Create a workspace name.
   - **Market Preferences**: Set default chart intervals.
   - **Workspace**: Input initial watchlist symbols (e.g., AAPL).
6. Click Finish. Verify you are routed to `/dashboard`.

## Flow 2: Market Terminal
1. Navigate to `/terminal`
2. Observe the top bar loading the global context.
3. Select an instrument in the search box.
4. Verify the Lightweight Charts load candlestick data without zero-filling.
5. Apply a "Trendline" or "Fibonacci" drawing on the chart using the left toolbar.

## Flow 3: AI Evidence & Signals
1. Click the "AI Signals" tab in the bottom pane.
2. Select an active signal.
3. In the right panel, observe the "Why this signal?" drawer.
4. Verify the LLM evidence pack metrics exactly match the UI (no hallucinations).

## Flow 4: Paper Trading
1. Open the trade panel on the right.
2. Enter a quantity and click "Buy".
3. Check the "Portfolio" tab to see the order history populate from the canonical backend API (React Query).

## Flow 5: Backtesting Lab
1. Navigate to `/backtest-lab`.
2. Select "MACD Crossover".
3. Click "Run Backtest".
4. Observe the polling for `job_id` and the final metrics displaying real data (no static fallbacks).
