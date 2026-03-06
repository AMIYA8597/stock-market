# PHASE 12 Quick Start — Stock Detail Page

**Status**: Ready to Begin  
**Estimated Time**: 3-5 days  
**Dependencies**: All completed ✅  

---

## Quick Overview

PHASE 12 builds the **Stock Detail Page** — a comprehensive single-stock view with TradingView charts, 7+ technical indicators, AI predictions, and research reports.

**Route**: `/market/[symbol]` (e.g., `/market/RELIANCE.NS`, `/market/TCS.NS`)

---

## Architecture

```
Stock Detail Page
├── Header Section
│   ├── Stock name + symbol
│   ├── Current price + daily change %
│   ├── 52-week high/low
│   ├── Market cap + sector
│   └── Watchlist button
│
├── Main Content (2-column)
│   ├── Left (2/3 width)
│   │   ├── TradingView Chart
│   │   │   ├── Timeframe selector (1m to 1M)
│   │   │   ├── Candlestick + Volume
│   │   │   └── Indicators overlay
│   │   │
│   │   ├── Technical Indicator Panels
│   │   │   ├── MACD
│   │   │   ├── RSI
│   │   │   ├── Bollinger Bands
│   │   │   ├── Stochastic
│   │   │   ├── ATR
│   │   │   ├── Ichimoku
│   │   │   └── Volume Profile
│   │   │
│   │   └── Pattern Recognition
│   │       ├── Head & Shoulders
│   │       ├── Double Top/Bottom
│   │       ├── Bullish Engulfing
│   │       ├── Support/Resistance
│   │       └── Trend lines
│   │
│   └── Right (1/3 width) - Tabbed
│       ├── Tab 1: AI Forecast
│       │   ├── 5-candle prediction
│       │   ├── Confidence bands
│       │   ├── Direction gauge
│       │   └── Probability score
│       │
│       ├── Tab 2: Research Report
│       │   ├── LLM-generated summary
│       │   ├── Bull/bear case
│       │   ├── Catalysts
│       │   └── Risk factors
│       │
│       ├── Tab 3: Fundamentals
│       │   ├── P/E, EV/EBITDA
│       │   ├── ROE, ROIC, FCFF
│       │   ├── Dividend yield
│       │   └── DCF valuation
│       │
│       └── Tab 4: Options (if applicable)
│           ├── Options chain
│           ├── IV smile curve
│           ├── Call/Put volume
│           └── Greeks
│
└── Bottom Section
    ├── Latest news (3 headlines)
    ├── Analyst ratings
    ├── Earnings calendar
    └── Insider trading
```

---

## Step-by-Step Build Plan

### Step 1: Create Page Files

```bash
# Create the directory
mkdir -p apps/web/src/app/market/[symbol]

# Create files
touch apps/web/src/app/market/[symbol]/page.tsx
touch apps/web/src/app/market/layout.tsx
touch apps/web/src/components/market/StockHeader.tsx
touch apps/web/src/components/market/TradingViewChart.tsx
touch apps/web/src/components/market/TechnicalIndicators.tsx
touch apps/web/src/components/market/AIForecast.tsx
touch apps/web/src/components/market/ResearchReport.tsx
touch apps/web/src/components/market/Fundamentals.tsx
touch apps/web/src/components/market/OptionsChain.tsx
touch apps/web/src/types/market-detail.ts
```

### Step 2: Implement Types

**File**: `src/types/market-detail.ts`

```typescript
export interface StockDetail {
  symbol: string;
  company_name: string;
  sector: string;
  market_cap: number;
  current_price: number;
  daily_change: number;
  daily_change_pct: number;
  week_52_high: number;
  week_52_low: number;
  volume: number;
  market_cap: number;
  pe_ratio?: number;
  eps?: number;
  dividend_yield?: number;
}

export interface OHLCV {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TechnicalIndicators {
  macd: { line: number; signal: number; histogram: number };
  rsi: number;
  bollinger_bands: { upper: number; middle: number; lower: number };
  stochastic: { k: number; d: number };
  atr: number;
  ichimoku: { tenkan: number; kijun: number; senkou_a: number; senkou_b: number };
  volume_profile: { price: number; count: number }[];
}

export interface AIPrediction {
  next_5_close: number[];
  confidence_lower_95: number;
  confidence_lower_25: number;
  confidence_upper_25: number;
  confidence_upper_95: number;
  direction: 'bullish' | 'bearish' | 'neutral';
  probability_up: number;
}

export interface ResearchReport {
  summary: string;
  bull_case: string;
  bear_case: string;
  catalysts: string[];
  risk_factors: string[];
  rating: 'buy' | 'hold' | 'sell';
  target_price: number;
}

export interface Fundamentals {
  pe_ratio: number;
  eps: number;
  market_cap: number;
  book_value: number;
  debt_to_equity: number;
  roe: number;
  roic: number;
  fcf: number;
  dividend_yield: number;
  div_payout_ratio: number;
  payout_ratio: number;
  fcf_growth: number;
  dcf_value: number;
  intrinsic_value: number;
  upside_downside: number; // %
}
```

### Step 3: Install TradingView Chart Library

```bash
cd apps/web
pnpm add lightweight-charts
pnpm add -D @types/lightweight-charts
```

### Step 4: Build TradingView Chart Component

**File**: `src/components/market/TradingViewChart.tsx`

```typescript
'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi } from 'lightweight-charts';
import type { OHLCV } from '@/types/market-detail';

interface TradingViewChartProps {
  data: OHLCV[];
  symbol: string;
  indicators?: {
    macdLine?: number[];
    macdSignal?: number[];
    rsiLine?: number[];
    bbUpper?: number[];
    bbMiddle?: number[];
    bbLower?: number[];
  };
}

export default function TradingViewChart({
  data,
  symbol,
  indicators,
}: TradingViewChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Calculate container height dynamically
    const height = containerRef.current.clientHeight || 500;

    // Create chart
    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: '#0A0B0E' },
        textColor: '#D1D5DB',
      },
      width: containerRef.current.clientWidth,
      height: height,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
    });

    // Create candlestick series
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#00E676',
      downColor: '#FF3B3B',
      borderUpColor: '#00E676',
      borderDownColor: '#FF3B3B',
      wickUpColor: '#00E676',
      wickDownColor: '#FF3B3B',
    });

    // Add OHLCV data (convert to seconds for trading view)
    const chartData = data.map((candle) => ({
      time: Math.floor(candle.timestamp / 1000) as any,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }));

    candleSeries.setData(chartData);

    // Add volume indicator
    const volumeSeries = chart.addHistogramSeries({
      color: '#00D4FF',
      borderColor: '#00D4FF',
    });

    const volumeData = data.map((candle) => ({
      time: Math.floor(candle.timestamp / 1000) as any,
      value: candle.volume,
    }));

    volumeSeries.setData(volumeData);

    // Fit chart to data
    chart.timeScale().fitContent();

    // Store references
    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;

    // Handle resize
    const handleResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: containerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data]);

  return (
    <div
      ref={containerRef}
      className="bg-background-secondary rounded-lg border border-background-tertiary"
      style={{ height: '500px' }}
    />
  );
}
```

### Step 5: Build AI Forecast Component

**File**: `src/components/market/AIForecast.tsx`

```typescript
'use client';

import React from 'react';
import { TrendingUp } from 'lucide-react';
import type { AIPrediction } from '@/types/market-detail';

interface AIForecastProps {
  prediction: AIPrediction;
  currentPrice: number;
}

export default function AIForecast({
  prediction,
  currentPrice,
}: AIForecastProps) {
  const avgPredicted =
    prediction.next_5_close.reduce((a, b) => a + b, 0) /
    prediction.next_5_close.length;
  const expectedMove = ((avgPredicted - currentPrice) / currentPrice) * 100;

  // Determine direction color
  const directionColor =
    prediction.direction === 'bullish'
      ? '#00E676'
      : prediction.direction === 'bearish'
        ? '#FF3B3B'
        : '#FFB800';

  return (
    <div className="space-y-6">
      {/* Direction Gauge */}
      <div className="flex items-center justify-center">
        <div className="relative w-32 h-32">
          {/* Semi-circle gauge */}
          <svg className="w-full h-full" viewBox="0 0 100 60">
            {/* Background track */}
            <path
              d="M 10 50 A 40 40 0 0 1 90 50"
              fill="none"
              stroke="#374151"
              strokeWidth="2"
            />
            {/* Filled track based on direction */}
            <path
              d={`M 10 50 A 40 40 0 0 1 ${prediction.probability_up}%${prediction.probability_up}`}
              fill="none"
              stroke={directionColor}
              strokeWidth="3"
            />
            {/* Pointer */}
            <line
              x1="50"
              y1="50"
              x2={`${50 + 30 * Math.cos((prediction.probability_up / 100) * Math.PI - Math.PI / 2)}`}
              y2={`${50 + 30 * Math.sin((prediction.probability_up / 100) * Math.PI - Math.PI / 2)}`}
              stroke={directionColor}
              strokeWidth="2"
            />
          </svg>

          {/* Center text */}
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-2xl font-bold" style={{ color: directionColor }}>
                {prediction.probability_up}%
              </div>
              <div className="text-xs text-gray-400">Upside</div>
            </div>
          </div>
        </div>
      </div>

      {/* Expected Move */}
      <div className="bg-background-tertiary rounded-lg p-4">
        <div className="text-sm text-gray-400 mb-1">Expected Move (5 candles)</div>
        <div
          className="text-2xl font-bold font-mono"
          style={{ color: expectedMove > 0 ? '#00E676' : '#FF3B3B' }}
        >
          {expectedMove > 0 ? '+' : ''}
          {expectedMove.toFixed(2)}%
        </div>
      </div>

      {/* Confidence Bands */}
      <div className="space-y-2">
        <div className="text-sm text-gray-400 mb-3">Confidence Bands</div>

        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-gray-400">95% Confidence</span>
            <span className="font-mono">₹{prediction.confidence_upper_95.toFixed(2)}</span>
          </div>
          <div className="w-full bg-background-tertiary h-1 rounded-full" />
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-gray-400">75% Confidence</span>
            <span className="font-mono">₹{prediction.confidence_upper_25.toFixed(2)}</span>
          </div>
          <div className="w-full bg-background-tertiary h-1 rounded-full" />
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-gray-400">Current Price</span>
            <span className="font-mono font-bold">₹{currentPrice.toFixed(2)}</span>
          </div>
          <div className="w-full bg-primary h-2 rounded-full" />
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-gray-400">75% Confidence</span>
            <span className="font-mono">₹{prediction.confidence_lower_25.toFixed(2)}</span>
          </div>
          <div className="w-full bg-background-tertiary h-1 rounded-full" />
        </div>

        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-gray-400">95% Confidence</span>
            <span className="font-mono">₹{prediction.confidence_lower_95.toFixed(2)}</span>
          </div>
          <div className="w-full bg-background-tertiary h-1 rounded-full" />
        </div>
      </div>

      {/* Direction Badge */}
      <div className="flex justify-center">
        <div
          className="px-4 py-2 rounded-lg font-semibold text-center"
          style={{
            backgroundColor:
              prediction.direction === 'bullish'
                ? '#00E67633'
                : prediction.direction === 'bearish'
                  ? '#FF3B3B33'
                  : '#FFB80033',
            color: directionColor,
          }}
        >
          {prediction.direction.toUpperCase()} Signal
        </div>
      </div>
    </div>
  );
}
```

### Step 6: Update Dashboard to Link to Detail Page

**File**: `src/components/dashboard/TopHoldingsCard.tsx` (update)

```typescript
// Add click handler to navigate to stock detail
onClick={() => router.push(`/market/${holding.symbol}`)}
```

---

## Key Implementation Details

### 1. TradingView Integration
- Lightweight Charts is lightweight (~40KB gzipped)
- Supports multiple series (candlestick, line, histogram)
- Auto-resize on window change
- Dark theme support

### 2. Multiple Timeframes
```typescript
const timeframes = ['1m', '5m', '15m', '1h', '4h', '1D', '1W', '1M'];

// API call varies by timeframe
const data = await apiClient.get(`/market/${symbol}/ohlcv?period=${timeframe}`);
```

### 3. Technical Indicators
Each indicator comes from Phase 4-5 backend:
```typescript
const indicators = await apiClient.get(`/market/${symbol}/indicators`);
```

### 4. AI Predictions
From Phase 9 AI Engine:
```typescript
const prediction = await apiClient.get(`/ai/forecast/${symbol}`);
```

### 5. Research Reports
From Phase 9 LLM Agent:
```typescript
const report = await apiClient.get(`/ai/research/${symbol}`);
```

---

## Testing Strategy

### Unit Tests
```typescript
// tests/components/TradingViewChart.test.tsx
test('renders chart without errors');
test('handles timeframe change');
test('updates indicators on data change');

// tests/components/AIForecast.test.tsx
test('displays correct direction gauge');
test('shows confidence bands');
test('calculates expected move correctly');
```

### E2E Tests
```typescript
// e2e/stock-detail.spec.ts
test('loads stock detail page');
test('chart updates on timeframe change');
test('prediction updates when fetched');
test('all tabs clickable');
test('mobile responsive');
```

---

## Dependencies to Add

```bash
pnpm add lightweight-charts
pnpm add react-router-dom  # For navigation (if not using next/router)
```

---

## Notes

1. **Chart Performance**: TradingView Lightweight Charts is highly optimized for real-time updates
2. **WebSocket Integration**: Replace API calls with WebSocket messages for live OHLCV data
3. **Indicators**: Can be calculated frontend or backend (recommend backend for accuracy)
4. **Caching**: Use React Query to cache charts (5-minute stale time)
5. **Mobile**: Adjust chart height for mobile (make it smaller, stack tabs vertically)

---

## Success Criteria

✅ TradingView chart renders with candlestick + volume  
✅ Multiple timeframes switchable  
✅ 7+ technical indicators display correctly  
✅ AI prediction shows with confidence bands  
✅ Research report tab with LLM content  
✅ Fundamentals tab with financial metrics  
✅ Responsive on mobile (chart stacks, tabs adjust)  
✅ Real-time updates via WebSocket-ready (mock for now)  
✅ No TypeScript errors (strict)  
✅ Performance: chart renders < 100ms  

---

## Launch Command

```bash
cd apps/web
pnpm run dev

# Visit http://localhost:3000/market/RELIANCE.NS
```

---

**Ready to Begin PHASE 12!** All dependencies are in place. TradingView integration is straightforward and performant. Estimated completion: **3-5 days**.
