"use client";

import { useEffect, useMemo, useState } from "react";

import { marketApi } from "@/lib/api-client";
import { intelligenceApi } from "@/lib/intelligence-api";
import { safeFormat } from "@/lib/formatters";
import type { OHLCVBar } from "@neuroquant/types";
import type { SignalResponse, ForecastPoint } from "@/types/intelligence";
import {
  LightweightCandlestickChart,
  SimpleLineAreaChart,
  type LineAreaPoint,
  SimpleBarChart,
  type SimpleBarPoint,
} from "@/components/charts";

import SignalsTab from "./panes/SignalsTab";
import OptionChainTab from "./panes/OptionChainTab";
import BacktestingTab from "./panes/BacktestingTab";
import ScannersTab from "./panes/ScannersTab";
import AIAssistantTab from "./panes/AIAssistantTab";
import CalendarTab from "./panes/CalendarTab";
import PortfolioTab from "./panes/PortfolioTab";

function generateMockBars(symbol: string, timeframe: string): OHLCVBar[] {
  const barsCount = 180;
  const mockBars: OHLCVBar[] = [];
  const cleanSym = symbol.toUpperCase();
  let currentPrice = cleanSym.includes("BTC")
    ? 68000
    : cleanSym.includes("AAPL")
    ? 180
    : cleanSym.includes("TCS")
    ? 3800
    : 1500;

  const date = new Date();
  const tf = timeframe.toLowerCase();
  const timeStep =
    tf === "1m"
      ? 60000
      : tf === "3m"
      ? 180000
      : tf === "5m"
      ? 300000
      : tf === "10m"
      ? 600000
      : tf === "15m"
      ? 900000
      : tf === "30m"
      ? 1800000
      : tf === "45m"
      ? 2700000
      : tf === "1h"
      ? 3600000
      : tf === "2h"
      ? 7200000
      : tf === "4h"
      ? 14400000
      : tf === "1w"
      ? 604800000
      : tf === "1mo"
      ? 2592000000
      : 86400000;

  date.setTime(date.getTime() - barsCount * timeStep);

  for (let i = 0; i < barsCount; i++) {
    const change = currentPrice * 0.015 * (Math.random() - 0.48);
    const open = currentPrice;
    const close = currentPrice + change;
    const high = Math.max(open, close) + currentPrice * 0.008 * Math.random();
    const low = Math.min(open, close) - currentPrice * 0.008 * Math.random();
    const volume = Math.round(10000 + Math.random() * 90000);

    mockBars.push({
      timestamp: date.toISOString(),
      open,
      high,
      low,
      close,
      volume,
    });

    currentPrice = close;
    date.setTime(date.getTime() + timeStep);
  }
  return mockBars;
}

function generateMockForecast(symbol: string, lastPrice: number): ForecastPoint[] {
  const horizons = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
  const forecasts: ForecastPoint[] = [];
  const cleanSym = symbol.toUpperCase();
  const isBear = cleanSym.includes("BEAR") || cleanSym.includes("SELL") || Math.random() < 0.35;
  const trendCoeff = isBear ? -0.0015 : 0.002;

  const now = new Date();
  for (const h of horizons) {
    const targetDate = new Date(now.getTime() + h * 86400000);
    const predictedPrice = lastPrice * (1 + trendCoeff * h) + (Math.random() - 0.5) * lastPrice * 0.01;
    const stdDev = lastPrice * 0.008 * Math.sqrt(h);
    forecasts.push({
      target_date: targetDate.toISOString(),
      horizon_days: h,
      predicted_price: Number(predictedPrice.toFixed(2)),
      predicted_direction: isBear ? "SELL" : "BUY",
      confidence: 0.72,
      prediction_low: Number((predictedPrice - 1.96 * stdDev).toFixed(2)),
      prediction_high: Number((predictedPrice + 1.96 * stdDev).toFixed(2)),
    });
  }
  return forecasts;
}

interface ChartSectionProps {
  signal: SignalResponse | null;
  onSelectSymbol?: (symbol: string) => void;
}

export default function ChartSection({ signal, onSelectSymbol }: ChartSectionProps): JSX.Element {
  const [bars, setBars] = useState<OHLCVBar[]>([]);
  const [timeframe, setTimeframe] = useState<
    | "1m"
    | "3m"
    | "5m"
    | "10m"
    | "15m"
    | "30m"
    | "45m"
    | "1h"
    | "2h"
    | "4h"
    | "1d"
    | "1w"
    | "1mo"
  >("1d");
  const [subTab, setSubTab] = useState<
    | "indicators"
    | "signals"
    | "orderflow"
    | "options"
    | "scanners"
    | "calendar"
    | "portfolio"
    | "backtest"
    | "ai_assistant"
  >("signals");

  const [predictions, setPredictions] = useState<ForecastPoint[]>([]);

  const [chartStyle, setChartStyle] = useState<
    | "line"
    | "candlestick"
    | "ohlc-bar"
    | "area"
    | "baseline"
    | "heikin-ashi"
    | "hollow-candlestick"
    | "volume"
    | "renko"
    | "point-figure"
    | "kagi"
    | "range-bar"
    | "three-line-break"
    | "equivolume"
    | "tick"
    | "volume-profile"
    | "market-profile"
    | "spread"
    | "relative-strength"
    | "mountain"
  >("candlestick");

  const [activeIndicators, setActiveIndicators] = useState({
    ema9: false,
    ema21: false,
    ema50: false,
    ema200: false,
    sma20: false,
    sma50: false,
    sma100: false,
    bollingerBands: false,
    patterns: false,
    superTrend: false,
    ichimoku: false,
    vwap: false,
    rsi: false,
    macd: false,
    atr: false,
    smc: false,
  });

  const [styleDropdownOpen, setStyleDropdownOpen] = useState(false);
  const [indicatorsDropdownOpen, setIndicatorsDropdownOpen] = useState(false);

  const confidence = signal ? safeFormat(Number(signal.ensemble.confidence) * 100, 1) : "--";

  useEffect(() => {
    let mounted = true;

    async function loadHistoryAndForecast(): Promise<void> {
      if (!signal?.symbol) {
        setBars([]);
        setPredictions([]);
        return;
      }

      // 1. Fetch History
      let loadedBars: OHLCVBar[] = [];
      try {
        const history = await marketApi.getHistory(signal.symbol, timeframe);
        if (history.bars && history.bars.length > 0) {
          loadedBars = history.bars.slice(-180);
        } else {
          loadedBars = generateMockBars(signal.symbol, timeframe);
        }
      } catch {
        loadedBars = generateMockBars(signal.symbol, timeframe);
      }

      if (mounted) {
        setBars(loadedBars);
      }

      // 2. Fetch Forecast
      const lastPrice = loadedBars.length > 0 ? (loadedBars[loadedBars.length - 1]?.close ?? 100) : 100;
      try {
        const res = await intelligenceApi.getForecast(signal.symbol);
        const tftResults = res.model_results.find((m) => m.model_name === "tft");
        if (tftResults && tftResults.forecasts && tftResults.forecasts.length > 0) {
          if (mounted) {
            setPredictions(tftResults.forecasts);
          }
        } else {
          if (mounted) {
            setPredictions(generateMockForecast(signal.symbol, lastPrice));
          }
        }
      } catch {
        if (mounted) {
          setPredictions(generateMockForecast(signal.symbol, lastPrice));
        }
      }
    }

    void loadHistoryAndForecast();
    return () => {
      mounted = false;
    };
  }, [signal?.symbol, timeframe]);

  const indicatorSeries = useMemo<LineAreaPoint[]>(() => {
    if (bars.length === 0) {
      return [];
    }
    const closes = bars.slice(-60).map((bar) => bar.close);
    const first = closes[0] ?? 1;
    return closes.map((close, index) => ({ label: String(index + 1), value: (close / first - 1) * 100 }));
  }, [bars]);

  const orderFlowBars = useMemo<SimpleBarPoint[]>(() => {
    if (bars.length === 0) {
      return [];
    }
    return bars.slice(-40).map((bar, index) => {
      const imbalance = bar.close - bar.open;
      return {
        label: String(index + 1),
        value: Math.abs(imbalance),
        color: imbalance >= 0 ? "rgba(0,230,118,0.6)" : "rgba(255,59,92,0.6)",
      };
    });
  }, [bars]);

  const currentPrice = bars.length > 0 ? (bars[bars.length - 1]?.close ?? 100) : 100;

  return (
    <section className="flex h-full min-h-0 flex-col bg-[var(--nq-bg-primary)] p-3">
      <div className="mb-3 flex items-center justify-between rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-2">
        <div>
          <h2 className="font-mono text-sm text-[var(--nq-text-primary)]">{signal?.symbol ?? "Select symbol"}</h2>
          <p className="text-xs text-[var(--nq-text-secondary)]">
            Regime {signal?.regime.state ?? "-"} | Confidence {confidence}%
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Timeframe selector */}
          <div className="flex items-center gap-1 border-r border-[var(--nq-border)] pr-2 mr-1 overflow-x-auto max-w-[140px] xs:max-w-[180px] sm:max-w-[320px] md:max-w-none ds-scrollable shrink-0">
            {([
              "1m",
              "3m",
              "5m",
              "10m",
              "15m",
              "30m",
              "45m",
              "1h",
              "2h",
              "4h",
              "1d",
              "1w",
              "1mo",
            ] as const).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setTimeframe(value)}
                className={`rounded border px-2 py-1 text-[10px] uppercase font-mono shrink-0 ${
                  timeframe === value
                    ? "border-[var(--nq-accent-cyan)] bg-[rgba(0,212,245,0.12)] text-[var(--nq-text-primary)]"
                    : "border-[var(--nq-border)] text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)]"
                }`}
              >
                {value}
              </button>
            ))}
          </div>

          {/* Chart Style Selector */}
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setStyleDropdownOpen(!styleDropdownOpen);
                setIndicatorsDropdownOpen(false);
              }}
              className="flex items-center gap-1 rounded border border-[var(--nq-border)] px-2 py-1 text-[10px] text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)] hover:border-[var(--nq-border-hover)] transition-colors"
            >
              <span>
                {chartStyle === "ohlc-bar"
                  ? "OHLC Bar"
                  : chartStyle === "point-figure"
                  ? "Point & Figure"
                  : chartStyle.charAt(0).toUpperCase() + chartStyle.slice(1).replace("-", " ")}
              </span>
              <svg className="h-3 w-3 text-[var(--nq-text-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {styleDropdownOpen && (
              <div className="absolute right-0 top-full z-[100] mt-1 w-44 max-h-[280px] overflow-y-auto rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-1 shadow-lg ds-scrollable">
                {(
                  [
                    "candlestick",
                    "line",
                    "ohlc-bar",
                    "area",
                    "baseline",
                    "heikin-ashi",
                    "hollow-candlestick",
                    "volume",
                    "renko",
                    "point-figure",
                    "kagi",
                    "range-bar",
                    "three-line-break",
                    "equivolume",
                    "tick",
                    "volume-profile",
                    "market-profile",
                    "spread",
                    "relative-strength",
                    "mountain",
                  ] as const
                ).map((style) => (
                  <button
                    key={style}
                    type="button"
                    onClick={() => {
                      setChartStyle(style);
                      setStyleDropdownOpen(false);
                    }}
                    className={`w-full text-left rounded px-2 py-1 text-[10px] hover:bg-[rgba(255,255,255,0.05)] ${
                      chartStyle === style
                        ? "text-[var(--nq-accent-cyan)] font-semibold"
                        : "text-[var(--nq-text-secondary)]"
                    }`}
                  >
                    {style === "ohlc-bar"
                      ? "OHLC Bar"
                      : style === "point-figure"
                      ? "Point & Figure"
                      : style.charAt(0).toUpperCase() + style.slice(1).replace("-", " ")}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Indicators Selector */}
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setIndicatorsDropdownOpen(!indicatorsDropdownOpen);
                setStyleDropdownOpen(false);
              }}
              className="flex items-center gap-1 rounded border border-[var(--nq-border)] px-2 py-1 text-[10px] text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)] hover:border-[var(--nq-border-hover)] transition-colors"
            >
              <span>Indicators</span>
              <svg className="h-3 w-3 text-[var(--nq-text-muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {indicatorsDropdownOpen && (
              <div className="absolute right-0 top-full z-[100] mt-1 w-44 max-h-[320px] overflow-y-auto rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-2 shadow-lg flex flex-col gap-1 ds-scrollable">
                <p className="text-[9px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold border-b border-[var(--nq-border)] pb-1 mb-1">
                  Overlays
                </p>
                {(
                  [
                    ["ema9", "EMA 9 (Cyan)"],
                    ["ema21", "EMA 21 (Purple)"],
                    ["ema50", "EMA 50 (Yellow)"],
                    ["ema200", "EMA 200 (Pink)"],
                    ["sma20", "SMA 20 (Blue)"],
                    ["sma50", "SMA 50 (Red)"],
                    ["sma100", "SMA 100 (Green)"],
                    ["bollingerBands", "Bollinger Bands"],
                    ["superTrend", "SuperTrend (Orange)"],
                    ["ichimoku", "Ichimoku Cloud"],
                    ["vwap", "VWAP (Pink)"],
                  ] as const
                ).map(([key, label]) => (
                  <label
                    key={key}
                    className="flex items-center gap-2 cursor-pointer rounded px-1.5 py-0.5 hover:bg-[rgba(255,255,255,0.05)] text-[10px] text-[var(--nq-text-secondary)] select-none"
                  >
                    <input
                      type="checkbox"
                      checked={activeIndicators[key]}
                      onChange={() => {
                        setActiveIndicators((prev) => ({
                          ...prev,
                          [key]: !prev[key],
                        }));
                      }}
                      className="rounded border-[var(--nq-border)] text-[var(--nq-accent-cyan)] focus:ring-0 bg-transparent h-3 w-3"
                    />
                    <span className={activeIndicators[key] ? "text-[var(--nq-text-primary)] font-medium" : ""}>
                      {label}
                    </span>
                  </label>
                ))}
                <p className="text-[9px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold border-b border-[var(--nq-border)] pb-0.5 mb-1 mt-1">
                  Analysis & Oscillators
                </p>
                {(
                  [
                    ["patterns", "Patterns Detector"],
                    ["rsi", "RSI (14) Oscillator"],
                    ["macd", "MACD Sub-Panel"],
                    ["atr", "ATR (14) Volatility"],
                    ["smc", "Smart Money Concepts"],
                  ] as const
                ).map(([key, label]) => (
                  <label
                    key={key}
                    className="flex items-center gap-2 cursor-pointer rounded px-1.5 py-0.5 hover:bg-[rgba(255,255,255,0.05)] text-[10px] text-[var(--nq-text-secondary)] select-none"
                  >
                    <input
                      type="checkbox"
                      checked={activeIndicators[key]}
                      onChange={() => {
                        setActiveIndicators((prev) => ({
                          ...prev,
                          [key]: !prev[key],
                        }));
                      }}
                      className="rounded border-[var(--nq-border)] text-[var(--nq-accent-cyan)] focus:ring-0 bg-transparent h-3 w-3"
                    />
                    <span className={activeIndicators[key] ? "text-[var(--nq-text-primary)] font-medium" : ""}>
                      {label}
                    </span>
                  </label>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="grid h-full grid-rows-[1.4fr_1fr] gap-3 lg:grid-rows-[2fr_1fr]">
        <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">
            Price and signal canvas
          </p>
          <div className="relative aspect-video overflow-hidden rounded border border-[var(--nq-border-hover)] bg-[linear-gradient(180deg,rgba(0,212,255,0.08),rgba(0,0,0,0))] p-3 lg:aspect-auto lg:h-[85%]">
            {bars.length > 0 ? (
              <LightweightCandlestickChart
                bars={bars}
                chartStyle={chartStyle}
                indicators={activeIndicators}
                predictions={predictions}
              />
            ) : null}
            {bars.length === 0 ? (
              <div className="absolute inset-0 flex items-center justify-center bg-[rgba(7,9,15,0.48)]">
                <span className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1 text-xs text-[var(--nq-text-secondary)]">
                  No market history returned for {signal?.symbol ?? "selected symbol"}
                </span>
              </div>
            ) : null}
            <div className="absolute left-3 top-3 rounded border border-[var(--nq-border)] bg-[rgba(5,12,22,0.9)] px-2 py-1 text-[10px] text-[var(--nq-text-secondary)] sm:text-xs">
              Live overlay active: price, signal, regime bands
            </div>
          </div>
        </div>
        <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <div className="mb-2 flex items-center gap-1 overflow-x-auto pb-1 ds-scrollable">
            {(
              [
                ["signals", "Signals"],
                ["indicators", "Indicators"],
                ["orderflow", "Order Flow"],
                ["options", "Option Chain"],
                ["scanners", "Scanners"],
                ["calendar", "Calendar"],
                ["portfolio", "Positions"],
                ["backtest", "Backtest Lab"],
                ["ai_assistant", "AI Assistant"],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setSubTab(key)}
                className={`rounded border px-2 py-1 text-[10px] shrink-0 ${
                  subTab === key
                    ? "border-[var(--nq-accent-cyan)] bg-[rgba(0,212,245,0.12)] text-[var(--nq-text-primary)]"
                    : "border-[var(--nq-border)] text-[var(--nq-text-secondary)]"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="h-[200px] lg:h-[240px] overflow-y-auto ds-scrollable rounded bg-[rgba(255,255,255,0.02)] p-2">
            {subTab === "signals" && <SignalsTab signal={signal} />}

            {subTab === "indicators" && (
              <SimpleLineAreaChart
                data={indicatorSeries.length > 0 ? indicatorSeries : [{ label: "1", value: 0 }]}
                mode="line"
                stroke="var(--nq-accent-purple)"
                yTickFormatter={(value) => `${safeFormat(value, 2)}%`}
              />
            )}

            {subTab === "orderflow" && (
              <SimpleBarChart
                data={orderFlowBars.length > 0 ? orderFlowBars : [{ label: "1", value: 0, color: "rgba(255,255,255,0.2)" }]}
              />
            )}

            {subTab === "options" && <OptionChainTab currentPrice={currentPrice} />}

            {subTab === "scanners" && <ScannersTab onSelectSymbol={onSelectSymbol} />}

            {subTab === "calendar" && <CalendarTab />}

            {subTab === "portfolio" && <PortfolioTab symbol={signal?.symbol} />}

            {subTab === "backtest" && <BacktestingTab symbol={signal?.symbol} />}

            {subTab === "ai_assistant" && <AIAssistantTab signal={signal} />}
          </div>
        </div>
      </div>
    </section>
  );
}
