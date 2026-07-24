/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
"use client";

import { useEffect, useMemo, useState } from "react";

import { marketApi } from "@/lib/api-client";
import { safeFormat } from "@/lib/formatters";
import type { OHLCVBar, Interval } from "@neuroquant/types";
import type { SignalResponse, ForecastPoint } from "@/types/intelligence";
import dynamic from "next/dynamic";
import {
  SimpleLineAreaChart,
  type LineAreaPoint,
  SimpleBarChart,
  type SimpleBarPoint,
} from "@/components/charts";
import { usePriceFeed } from "@/hooks/usePriceFeed";
import { useHistoryQuery } from "@/hooks/queries/useMarketData";
import { useQuery } from "@tanstack/react-query";

const LightweightCandlestickChart = dynamic(
  () => import("@/components/charts").then((mod) => mod.LightweightCandlestickChart),
  { ssr: false }
);

import SignalsTab from "./panes/SignalsTab";
import OptionChainTab from "./panes/OptionChainTab";
import BacktestingTab from "./panes/BacktestingTab";
import ScannersTab from "./panes/ScannersTab";
import AIAssistantTab from "./panes/AIAssistantTab";
import CalendarTab from "./panes/CalendarTab";
import PortfolioTab from "./panes/PortfolioTab";

interface ChartSectionProps {
  signal: SignalResponse | null;
  onSelectSymbol?: (symbol: string) => void;
  defaultSymbol?: string;
}

function getIsMarketClosed(): boolean {
  const options = { timeZone: "Asia/Kolkata" };
  let istString: string;
  try {
    istString = new Date().toLocaleString("en-US", options);
  } catch (e) {
    istString = new Date().toLocaleString();
  }
  const istDate = new Date(istString);
  const day = istDate.getDay(); // 0 = Sunday, 6 = Saturday
  const hours = istDate.getHours();
  const minutes = istDate.getMinutes();
  const totalMinutes = hours * 60 + minutes;

  const isOpenDay = day >= 1 && day <= 5; // Monday to Friday
  const isOpenTime = totalMinutes >= 555 && totalMinutes < 930; // 9:15 to 15:30
  return !(isOpenDay && isOpenTime);
}

export default function ChartSection({ signal, onSelectSymbol, defaultSymbol }: ChartSectionProps): JSX.Element {
  // Use signal's symbol or defaultSymbol to load data even before signal arrives
  const activeSymbol = signal?.symbol ?? defaultSymbol ?? null;
  const [isClosed, setIsClosed] = useState<boolean>(getIsMarketClosed());

  useEffect(() => {
    const timer = setInterval(() => {
      setIsClosed(getIsMarketClosed());
    }, 10000);
    return () => clearInterval(timer);
  }, []);

  const [bars, setBars] = useState<OHLCVBar[]>([]);
  const [timeframe, setTimeframe] = useState<Interval>("1d");
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
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historySource, setHistorySource] = useState<string | null>(null);
  const [forecastError, setForecastError] = useState<string | null>(null);

  // 1. Fetch History using React Query
  const { data: historyData, error: queryError, isLoading: queryLoading } = useHistoryQuery(activeSymbol || "", timeframe);

  // 2. Fetch Forecast using React Query
  const { data: forecastData, error: qForecastError } = useQuery({
    queryKey: ["forecast", signal?.symbol],
    queryFn: async () => {
      if (!signal?.symbol) return [];
      const response = await fetch("/api/v1/predictions/forecast", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: signal.symbol, horizons: [1, 3, 5, 10, 21] }),
      });
      if (!response.ok) throw new Error(`Failed with status ${response.status}`);
      const data = await response.json();
      return (data.forecast || []).map((pt: any) => ({
        target_date: pt.target_date,
        horizon_days: pt.horizon_days,
        predicted_price: pt.predicted_price,
        predicted_direction: pt.change_pct >= 0 ? "BUY" : "SELL",
        confidence: data.confidence ?? 0.5,
        prediction_low: pt.prediction_low,
        prediction_high: pt.prediction_high,
        change_pct: pt.change_pct,
      }));
    },
    enabled: !!signal?.symbol,
  });

  const isLoading = queryLoading;

  // Live Price Feed Integration for real-time chart updates
  const { ticks } = usePriceFeed(activeSymbol ? [activeSymbol] : []);
  const liveTick = activeSymbol ? ticks.get(activeSymbol.toUpperCase()) : null;

  useEffect(() => {
    if (!liveTick || bars.length === 0) return;

    setBars((prevBars) => {
      if (prevBars.length === 0) return prevBars;
      const lastBar = prevBars[prevBars.length - 1];
      if (!lastBar) return prevBars;

      const tickTime = new Date(liveTick.timestamp).getTime();
      const lastBarTime = new Date(lastBar.timestamp).getTime();

      // Determine timeframe length in milliseconds
      let intervalMs = 24 * 60 * 60 * 1000; // default 1d
      if (timeframe === "1m") intervalMs = 60 * 1000;
      else if (timeframe === "3m") intervalMs = 3 * 60 * 1000;
      else if (timeframe === "5m") intervalMs = 5 * 60 * 1000;
      else if (timeframe === "10m") intervalMs = 10 * 60 * 1000;
      else if (timeframe === "15m") intervalMs = 15 * 60 * 1000;
      else if (timeframe === "30m") intervalMs = 30 * 60 * 1000;
      else if (timeframe === "45m") intervalMs = 45 * 60 * 1000;
      else if (timeframe === "1h") intervalMs = 60 * 60 * 1000;
      else if (timeframe === "2h") intervalMs = 2 * 60 * 60 * 1000;
      else if (timeframe === "4h") intervalMs = 4 * 60 * 60 * 1000;
      else if (timeframe === "1w") intervalMs = 7 * 24 * 60 * 60 * 1000;
      else if (timeframe === "1mo") intervalMs = 30 * 24 * 60 * 60 * 1000;

      const tickBucketTime = Math.floor(tickTime / intervalMs) * intervalMs;
      const lastBarBucketTime = Math.floor(lastBarTime / intervalMs) * intervalMs;

      const updatedBars = [...prevBars];

      if (tickBucketTime === lastBarBucketTime) {
        // Update the last candle
        const updatedBar = { ...lastBar };
        updatedBar.close = liveTick.price;
        updatedBar.high = Math.max(updatedBar.high, liveTick.price);
        updatedBar.low = Math.min(updatedBar.low, liveTick.price);
        updatedBars[updatedBars.length - 1] = updatedBar;
      } else if (tickBucketTime > lastBarBucketTime) {
        // Append a new candle
        const newBar: OHLCVBar = {
          timestamp: new Date(tickBucketTime).toISOString(),
          open: liveTick.price,
          high: liveTick.price,
          low: liveTick.price,
          close: liveTick.price,
          volume: 0,
        };
        updatedBars.push(newBar);
        if (updatedBars.length > 180) {
          updatedBars.shift();
        }
      }

      return updatedBars;
    });
  }, [liveTick, timeframe, bars.length]);

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
    if (forecastData) {
      setPredictions(forecastData);
      setForecastError(null);
    }
  }, [forecastData]);

  useEffect(() => {
    if (qForecastError) {
      setPredictions([]);
      const errMsg = qForecastError instanceof Error ? qForecastError.message : "Unable to load forecast.";
      if (errMsg.includes("503")) {
        setForecastError("Prediction model not yet trained");
      } else {
        setForecastError(errMsg);
      }
    }
  }, [qForecastError]);

  useEffect(() => {
    if (!activeSymbol) {
      setBars([]);
      setHistoryError(null);
      setHistorySource(null);
      return;
    }
    
    if (historyData) {
      if (historyData.bars && historyData.bars.length > 0) {
        setBars(historyData.bars.slice(-300));
        setHistoryError(null);
        setHistorySource(historyData.source ?? "yfinance");
      } else {
        setHistoryError(`No ${timeframe} history returned for ${activeSymbol}.`);
        setHistorySource(null);
        setBars([]);
      }
    }
  }, [historyData, activeSymbol, timeframe]);

  useEffect(() => {
    if (queryError) {
      setHistoryError(queryError instanceof Error ? queryError.message : "Unable to load market history.");
      setHistorySource(null);
    }
  }, [queryError]);

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
  const displaySymbol = activeSymbol ?? "Select symbol";

  return (
    <section className="flex h-full min-h-0 flex-col bg-[var(--nq-bg-primary)]">
      {/* Chart Header */}
      <div className="mb-0 flex shrink-0 flex-col md:flex-row flex-wrap md:items-center justify-between border-b border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-2 gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="font-mono text-sm font-bold text-[var(--nq-text-primary)]">{displaySymbol}</h2>
            {historySource && (
              <span className={`rounded border px-1.5 py-0.5 text-[9px] font-mono font-semibold uppercase tracking-wider ${
                historySource.toLowerCase() === "nse"
                  ? "bg-[rgba(0,230,118,0.12)] border-[rgba(0,230,118,0.3)] text-[#00E676]"
                  : "bg-[rgba(255,255,255,0.05)] border-[var(--nq-border)] text-[var(--nq-text-muted)]"
              }`}>
                {historySource.toLowerCase() === "nse" ? "NSE live" : `${historySource} (delayed)`}
              </span>
            )}
            {isClosed && activeSymbol && (
              <span className="rounded bg-[rgba(255,59,92,0.12)] border border-[rgba(255,59,92,0.3)] px-2 py-0.5 text-[10px] font-medium text-[#FF3B5C]">
                Market Closed
              </span>
            )}
          </div>
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

      {/* Main chart + tabs area: use explicit flex layout */}
      <div className="flex min-h-0 flex-1 flex-col gap-0">
        {/* CHART AREA - takes most of the vertical space */}
        <div className="relative min-h-[300px] flex-1 border border-[var(--nq-border)] bg-[var(--nq-bg-card)] rounded mx-3 mb-2">
          <div className="absolute inset-0 flex flex-col">
            <div className="flex shrink-0 items-center gap-2 px-3 pt-2 pb-1">
              <p className="text-[9px] uppercase tracking-[0.12em] text-[var(--nq-text-secondary)] font-semibold">
                Price &amp; Signal Canvas
              </p>
              {liveTick && (
                <span className="font-mono text-xs font-bold text-[#00E676]">
                  ₹{liveTick.price.toFixed(2)}
                  <span className={`ml-1 text-[10px] ${liveTick.change_pct >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
                    {liveTick.change_pct >= 0 ? "+" : ""}{liveTick.change_pct.toFixed(2)}%
                  </span>
                </span>
              )}
            </div>
            <div className="relative min-h-0 flex-1">
              {isLoading ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
                  <div className="h-8 w-8 rounded-full border-2 border-[var(--nq-accent-cyan)] border-t-transparent animate-spin" />
                  <span className="text-xs text-[var(--nq-text-secondary)]">Loading {activeSymbol} {timeframe}...</span>
                </div>
              ) : historyError ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
                  <div className="h-12 w-12 rounded-full bg-[rgba(255,59,92,0.1)] border border-[rgba(255,59,92,0.3)] flex items-center justify-center">
                    <span className="text-[#FF3B5C] text-lg">!</span>
                  </div>
                  <span className="text-xs text-[#FF3B5C] text-center max-w-[200px]">{historyError}</span>
                </div>
              ) : !activeSymbol ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
                  <div className="h-12 w-12 rounded-full bg-[rgba(0,212,245,0.08)] border border-[rgba(0,212,245,0.2)] flex items-center justify-center">
                    <span className="text-[var(--nq-accent-cyan)] text-lg">📈</span>
                  </div>
                  <span className="text-xs text-[var(--nq-text-secondary)]">Select a symbol from the watchlist to load chart data</span>
                </div>
              ) : bars.length === 0 ? (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
                  <div className="h-12 w-12 rounded-full bg-[rgba(255,255,255,0.05)] border border-[var(--nq-border)] flex items-center justify-center">
                    <span className="text-[var(--nq-text-secondary)] text-lg">∅</span>
                  </div>
                  <span className="text-xs text-[var(--nq-text-secondary)] text-center max-w-[200px]">No {timeframe} data available for {activeSymbol}</span>
                </div>
              ) : (
                <LightweightCandlestickChart
                  bars={bars}
                  chartStyle={chartStyle}
                  indicators={activeIndicators}
                  predictions={predictions}
                  symbol={activeSymbol}
                />
              )}
            </div>
            {(historyError || forecastError) && bars.length > 0 ? (
              <div className="shrink-0 flex flex-wrap gap-2 px-3 pb-2 text-[11px]">
                {historyError ? (
                  <span className="rounded border border-[rgba(255,59,92,0.35)] bg-[rgba(255,59,92,0.08)] px-2 py-1 text-[var(--nq-accent-red)]">
                    {historyError}
                  </span>
                ) : null}
                {forecastError ? (
                  <span className="rounded border border-[rgba(255,193,7,0.35)] bg-[rgba(255,193,7,0.08)] px-2 py-1 text-[#F7C948]">
                    Forecast: {forecastError}
                  </span>
                ) : null}
              </div>
            ) : null}
          </div>
        </div>

        {/* BOTTOM PANEL - sub-tabs */}
        <div className="flex flex-col shrink-0 border border-[var(--nq-border)] bg-[var(--nq-bg-card)] rounded mx-3 mb-3 h-64 lg:h-[280px]">
          <div className="flex shrink-0 items-center gap-1 border-b border-[var(--nq-border)] px-2 pt-1 pb-1 overflow-x-auto ds-scrollable">
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
          <div className="flex-1 min-h-0 overflow-y-auto ds-scrollable rounded bg-[rgba(255,255,255,0.02)] p-2">
            {subTab === "signals" && <SignalsTab signal={signal} forecast={predictions} />}

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
