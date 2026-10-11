/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "@/i18n/navigation";
import { intelligenceApi } from "@/lib/intelligence-api";
import { marketApi, predictionsApi } from "@/lib/api-client";
import {
  contractsApi,
  type CounterfactualResponse,
  type ExplainAttentionResponse,
  type ExplainShapResponse,
  type MarketMover,
} from "@/lib/contracts-api";
import { usePriceFeed } from "@/hooks/usePriceFeed";
import { AmbientLucideBackground } from "@/components/common/ambient-lucide-background";
import {
  ChartCard,
  SimpleDonutChart,
  type DonutSlice,
  SimpleBarChart,
  type SimpleBarPoint,
} from "@/components/charts";
import dynamic from "next/dynamic";
import { Skeleton } from "@neuroquant/ui";
import { type PriceBar } from "@/utils/chartFormatters";
import { StockQuoteHeader } from "./StockQuoteHeader";
import { ohlcvBarSchema } from "@neuroquant/types";
import type { ModelEnsemble, Prediction, Quote } from "@neuroquant/types";
import type { SignalResponse } from "@/types/intelligence";

const LightweightCandlestickChart = dynamic(
  () => import("@/components/charts/LightweightCandlestickChart").then(mod => mod.LightweightCandlestickChart),
  { ssr: false, loading: () => <div className="h-[360px] w-full"><Skeleton className="h-full w-full rounded" /></div> }
);

interface StockLiveContractContentProps {
  symbol: string;
}

const INR_FORMATTER = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 2,
  minimumFractionDigits: 2,
});

const PERCENT_FORMATTER = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 2,
  minimumFractionDigits: 2,
});

function formatInr(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return INR_FORMATTER.format(value);
}

function formatPercent(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return `${value >= 0 ? "+" : ""}${PERCENT_FORMATTER.format(value)}%`;
}

export function StockLiveContractContent({ symbol }: StockLiveContractContentProps): JSX.Element {
  const [activeTab, setActiveTab] = useState<"fundamentals" | "analysis" | "similar">("fundamentals");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [ensemble, setEnsemble] = useState<ModelEnsemble | null>(null);
  const [signal, setSignal] = useState<SignalResponse | null>(null);
  const [shap, setShap] = useState<ExplainShapResponse | null>(null);
  const [attention, setAttention] = useState<ExplainAttentionResponse | null>(null);
  const [counterfactuals, setCounterfactuals] = useState<CounterfactualResponse[]>([]);
  const [similarAssets, setSimilarAssets] = useState<MarketMover[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [predictionError, setPredictionError] = useState<boolean>(false);

  // Candlestick Chart States
  const [chartInterval, setChartInterval] = useState<
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
  const [chartBars, setChartBars] = useState<PriceBar[]>([]);
  const [chartLoading, setChartLoading] = useState<boolean>(false);
  const [chartStyle, setChartStyle] = useState<
    | "line" | "candlestick" | "ohlc-bar" | "area" | "baseline" | "heikin-ashi"
    | "hollow-candlestick" | "volume" | "renko" | "point-figure" | "kagi"
    | "range-bar" | "three-line-break" | "equivolume" | "tick"
    | "volume-profile" | "market-profile" | "spread" | "relative-strength" | "mountain"
    | "vwap" | "anchored-vwap" | "cvd" | "open-interest" | "oi-price"
    | "put-call-ratio" | "iv-smile" | "volatility-cone" | "correlation-heatmap"
    | "rolling-correlation" | "returns-distribution" | "histogram-returns"
    | "drawdown" | "rolling-volatility" | "rolling-sharpe" | "rolling-beta"
    | "fibonacci" | "pivot-points" | "ichimoku-standalone" | "elliott-wave" | "gann"
  >("candlestick");
  const [chartHeight, setChartHeight] = useState<number>(420);
  const [styleDropdownOpen, setStyleDropdownOpen] = useState(false);
  const [indicatorsDropdownOpen, setIndicatorsDropdownOpen] = useState(false);
  const [activeIndicators, setActiveIndicators] = useState({
    ema9: false,
    ema21: true,
    ema50: true,
    ema200: false,
    sma20: false,
    sma50: false,
    sma100: false,
    bollingerBands: true,
    patterns: true,
    superTrend: true,
    ichimoku: false,
    vwap: true,
    rsi: true,
    macd: true,
    atr: true,
    smc: true,
  });
  const [predictions, setPredictions] = useState<{ target_date: string; predicted_price: number; prediction_low?: number; prediction_high?: number }[]>([]);
  const [forecastError, setForecastError] = useState<string | null>(null);

  const chartControlsRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (chartControlsRef.current && !chartControlsRef.current.contains(e.target as Node)) {
        setStyleDropdownOpen(false);
        setIndicatorsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const { ticks, status } = usePriceFeed([symbol]);
  const liveTick = ticks.get(symbol.toUpperCase());

  // Handle chart height based on breakpoints
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 640) {
        setChartHeight(280);
      } else if (window.innerWidth < 1024) {
        setChartHeight(360);
      } else {
        setChartHeight(420);
      }
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Fetch chart history when symbol or interval changes
  useEffect(() => {
    let isMounted = true;

    async function loadChartHistory() {
      if (!symbol) return;
      setChartLoading(true);

      let period = "1y";
      if (chartInterval === "1m" || chartInterval === "3m") {
        period = "5d";
      } else if (
        chartInterval === "5m" ||
        chartInterval === "10m" ||
        chartInterval === "15m" ||
        chartInterval === "30m" ||
        chartInterval === "45m"
      ) {
        period = "1mo";
      } else if (chartInterval === "1h" || chartInterval === "2h" || chartInterval === "4h") {
        period = "3mo";
      } else if (chartInterval === "1d") {
        period = "1y";
      } else if (chartInterval === "1w" || chartInterval === "1mo") {
        period = "5y";
      }

      try {
        const historyRes = await marketApi.getHistory(symbol, chartInterval, undefined, undefined, period);
        if (isMounted) {
          if (historyRes?.bars) {
            const mapped: PriceBar[] = [];
            for (const b of historyRes.bars) {
              const parsed = ohlcvBarSchema.safeParse(b);
              if (parsed.success) {
                mapped.push({
                  timestamp: parsed.data.timestamp,
                  open: parsed.data.open,
                  high: parsed.data.high,
                  low: parsed.data.low,
                  close: parsed.data.close,
                  volume: parsed.data.volume,
                });
              }
            }
            setChartBars(mapped);
          } else {
            setChartBars([]);
          }
        }
      } catch (err) {
        if (isMounted) {
          setChartBars([]);
        }
      } finally {
        if (isMounted) {
          setChartLoading(false);
        }
      }
    }

    void loadChartHistory();

    return () => {
      isMounted = false;
    };
  }, [symbol, chartInterval]);

  // Fetch all other data on symbol change
  useEffect(() => {
    let isMounted = true;

    async function load(): Promise<void> {
      setError(null);

      const results = await Promise.allSettled([
        marketApi.getQuote(symbol),
        predictionsApi.getLatest(symbol),
        predictionsApi.getEnsemble(symbol),
        intelligenceApi.getSignal(symbol),
        contractsApi.getExplainShap(symbol),
        contractsApi.getExplainAttention(symbol, "tft"),
        contractsApi.getCounterfactuals(symbol, { target_direction: "BUY", num_cfs: 3 }),
        contractsApi.getMovers("NSE", "momentum"),
      ]);

      const quoteResult = results[0];
      const predictionResult = results[1];
      const ensembleResult = results[2];
      const signalResult = results[3];

      if (!isMounted) {
        return;
      }

      if (quoteResult.status === "fulfilled") {
        setQuote(quoteResult.value);
      } else {
        setError("Unable to load market quote contract.");
      }

      if (predictionResult.status === "fulfilled") {
        setPrediction(predictionResult.value);
        setPredictionError(false);
      } else {
        setPredictionError(true);
      }
      if (ensembleResult.status === "fulfilled") {
        setEnsemble(ensembleResult.value);
      }
      if (signalResult.status === "fulfilled") {
        setSignal(signalResult.value);
      }

      if (quoteResult.status === "rejected") {
        setError("Unable to load market quote contract.");
      }

      const shapResult = results[4];
      const attentionResult = results[5];
      const counterfactualResult = results[6];
      const similarAssetsResult = results[7];

      if (shapResult.status === "fulfilled") {
        setShap(shapResult.value);
      }

      if (attentionResult.status === "fulfilled") {
        setAttention(attentionResult.value);
      }

      if (counterfactualResult.status === "fulfilled") {
        setCounterfactuals(counterfactualResult.value);
      }

      if (similarAssetsResult.status === "fulfilled") {
        setSimilarAssets(similarAssetsResult.value.filter((item) => item.ticker.toUpperCase() !== symbol.toUpperCase()).slice(0, 6));
      }
    }

    void load();

    return () => {
      isMounted = false;
    };
  }, [symbol]);

  // Fetch AI/ML multi-horizon forecast predictions
  useEffect(() => {
    if (!symbol) { setPredictions([]); return; }
    let active = true;
    intelligenceApi
      .getMultiHorizonForecast(symbol)
      .then((points) => {
        if (!active) return;
        setPredictions(points);
        setForecastError(points.length === 0 ? "No forecast data yet" : null);
      })
      .catch(() => {
        if (!active) return;
        setPredictions([]);
        setForecastError("Forecast unavailable");
      });
    return () => { active = false; };
  }, [symbol]);

  const latestPrice = liveTick?.price ?? quote?.price;
  const latestChangePct = liveTick?.change_pct ?? quote?.change_percent;

  const modelWeightSlices = useMemo<DonutSlice[]>(() => {
    if (!signal?.model_weights) {
      return [];
    }

    const palette = [
      "var(--nq-accent-cyan)",
      "var(--nq-accent-green)",
      "var(--nq-accent-amber)",
      "var(--nq-accent-purple)",
      "var(--nq-accent-red)",
      "#6FD3F5",
    ];

    return Object.entries(signal.model_weights)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([name, value], index) => ({
        name,
        value,
        color: palette[index % palette.length] ?? "var(--nq-accent-cyan)",
      }));
  }, [signal?.model_weights]);

  const ensembleBars = useMemo<SimpleBarPoint[]>(() => {
    return (ensemble?.models ?? []).slice(0, 6).map((model) => ({
      label: model.name.replace(/_/g, " ").slice(0, 12),
      value: model.weight,
      color: "var(--nq-accent-cyan)",
    }));
  }, [ensemble?.models]);

  const derivedFundamentals = useMemo(() => {
    return {
      marketCap: quote ? quote.price * quote.volume : null,
      pe: null as number | null,
      pb: null as number | null,
      eps: null as number | null,
      evEbitda: null as number | null,
      netMargin: null as number | null,
    };
  }, [quote]);

  const shapBars = useMemo<SimpleBarPoint[]>(() => {
    return (shap?.feature_contributions ?? []).slice(0, 8).map((item) => ({
      label: item.name.slice(0, 12),
      value: Math.abs(item.shap_val),
      color: item.shap_val >= 0 ? "rgba(0,230,118,0.65)" : "rgba(255,59,92,0.65)",
    }));
  }, [shap?.feature_contributions]);

  const attentionHeatCells = useMemo(() => {
    return (attention?.weights ?? []).slice(0, 8).flatMap((row, headIndex) => row.slice(0, 24).map((value, stepIndex) => ({ headIndex, stepIndex, value })));
  }, [attention?.weights]);

  // Signal Badge and Color Variables based on Direction from extended response
  const signalDirection = signal?.ensemble.direction ?? "NEUTRAL";
  
  const badgeClass =
    signalDirection === "STRONG_BUY"
      ? "text-[#00E676] border-[rgba(0,230,118,0.3)] bg-[rgba(0,230,118,0.08)]"
      : signalDirection === "BUY"
        ? "text-[#00E676] border-[rgba(0,230,118,0.2)] bg-[rgba(0,230,118,0.05)]"
        : signalDirection === "STRONG_SELL"
          ? "text-[#FF3B5C] border-[rgba(255,59,92,0.3)] bg-[rgba(255,59,92,0.08)]"
          : signalDirection === "SELL"
            ? "text-[#FF3B5C] border-[rgba(255,59,92,0.2)] bg-[rgba(255,59,92,0.05)]"
            : "text-[#FFB800] border-[rgba(255,184,0,0.2)] bg-[rgba(255,184,0,0.05)]";

  const isPulsing = signalDirection === "STRONG_BUY" || signalDirection === "STRONG_SELL";
  const dotColor =
    signalDirection === "STRONG_BUY" || signalDirection === "BUY"
      ? "bg-[#00E676]"
      : signalDirection === "STRONG_SELL" || signalDirection === "SELL"
        ? "bg-[#FF3B5C]"
        : "bg-[#FFB800]";

  return (
    <main className="relative min-h-screen overflow-hidden bg-[var(--nq-bg-base)] px-4 py-6 text-[var(--nq-text-primary)] sm:px-6 lg:px-8">
      <AmbientLucideBackground className="opacity-70" />
      <div className="relative z-10 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold">{symbol}</h1>
          <p className="mt-1 text-sm text-[var(--nq-text-secondary)]">Live market + signal contracts with websocket tick overlay.</p>
        </div>
          <div className="grid w-full grid-cols-2 gap-2 text-xs sm:w-auto items-center">
            <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-2 flex items-center gap-2">
              Price {formatInr(latestPrice)}
              <span
                className={`ml-2 rounded border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ${
                  (liveTick?.source === "realtime" || quote?.source === "realtime")
                    ? "text-[#00E676] border-[#00E676] bg-[rgba(0,230,118,0.1)]"
                    : (liveTick?.source === "computed" || quote?.source === "computed")
                      ? "text-[#B388FF] border-[#B388FF] bg-[rgba(179,136,255,0.1)]"
                      : "text-[#FFB800] border-[#FFB800] bg-[rgba(255,184,0,0.1)]"
                }`}
              >
                {(liveTick?.source === "realtime" || quote?.source === "realtime") ? "Real-time" : (liveTick?.source === "computed" || quote?.source === "computed") ? "Computed" : "Delayed"}
              </span>
            </div>
            <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-2">Day {formatPercent(latestChangePct)}</div>
          </div>
      </div>

      <p className="relative z-10 mt-2 text-xs text-[var(--nq-text-secondary)]">WS status: {status}</p>
      {error ? <p className="mt-2 text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <section className="relative z-10 mt-6 grid gap-4 xl:grid-cols-[1fr_320px]">
        <ChartCard title={`Price History (${chartInterval.toUpperCase()})`} subtitle="Live interactive candlestick overlays">
          {/* Timeframe + Chart Style + Indicators controls */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--nq-border)] pb-3 mb-3">
            <div className="flex items-center gap-1 overflow-x-auto ds-scrollable py-1">
              {(["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1mo"] as const).map((interval) => (
                <button
                  key={interval}
                  type="button"
                  onClick={() => setChartInterval(interval)}
                  className={`rounded border px-2 py-1 text-[10px] font-semibold font-mono transition-colors uppercase whitespace-nowrap ${
                    chartInterval === interval
                      ? "border-[var(--nq-accent-cyan)] bg-[rgba(0,212,245,0.12)] text-[var(--nq-text-primary)]"
                      : "border-[var(--nq-border)] text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)] hover:border-[var(--nq-border-hover)]"
                  }`}
                >
                  {interval}
                </button>
              ))}
            </div>
            <div ref={chartControlsRef} className="flex items-center gap-2">
              {/* Chart Style Dropdown - 20 types */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => { setStyleDropdownOpen(!styleDropdownOpen); setIndicatorsDropdownOpen(false); }}
                  className="flex items-center gap-1 rounded border border-[var(--nq-border)] px-2.5 py-1 text-xs text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)] hover:border-[var(--nq-border-hover)] transition-colors"
                >
                  <span className="capitalize">{chartStyle === "ohlc-bar" ? "OHLC Bar" : chartStyle === "point-figure" ? "Point & Figure" : chartStyle.replace(/-/g, " ")}</span>
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                </button>
                {styleDropdownOpen && (
                  <div className="absolute right-0 top-full z-[100] mt-1 w-48 max-h-[320px] overflow-y-auto rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-1 shadow-lg ds-scrollable">
                    {([
                      "candlestick", "line", "ohlc-bar", "area", "baseline", "heikin-ashi",
                      "hollow-candlestick", "volume", "renko", "point-figure", "kagi",
                      "range-bar", "three-line-break", "equivolume", "tick",
                      "volume-profile", "market-profile", "spread", "relative-strength", "mountain",
                      "vwap", "anchored-vwap", "cvd", "open-interest", "oi-price",
                      "put-call-ratio", "iv-smile", "volatility-cone", "correlation-heatmap",
                      "rolling-correlation", "returns-distribution", "histogram-returns",
                      "drawdown", "rolling-volatility", "rolling-sharpe", "rolling-beta",
                      "fibonacci", "pivot-points", "ichimoku-standalone", "elliott-wave", "gann",
                    ] as const).map((style) => (
                      <button
                        key={style}
                        type="button"
                        onClick={() => { setChartStyle(style); setStyleDropdownOpen(false); }}
                        className={`w-full text-left rounded px-2 py-1 text-xs hover:bg-[rgba(255,255,255,0.05)] ${chartStyle === style ? "text-[var(--nq-accent-cyan)] font-semibold" : "text-[var(--nq-text-secondary)]"}`}
                      >
                        {(() => {
                          const unavailable = ["open-interest", "oi-price", "put-call-ratio", "iv-smile", "volatility-cone", "correlation-heatmap", "rolling-correlation", "elliott-wave", "gann"];
                          const label = style === "ohlc-bar" ? "OHLC Bar" : style === "point-figure" ? "Point & Figure" : style === "cvd" ? "Cumulative Volume Delta" : style === "oi-price" ? "OI + Price" : style === "iv-smile" ? "IV Smile/Skew" : style === "vwap" ? "VWAP" : style === "anchored-vwap" ? "Anchored VWAP" : style.charAt(0).toUpperCase() + style.slice(1).replace(/-/g, " ");
                          return unavailable.includes(style) ? `${label} ⚠` : label;
                        })()}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              {/* Indicators Dropdown - 16 indicators */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => { setIndicatorsDropdownOpen(!indicatorsDropdownOpen); setStyleDropdownOpen(false); }}
                  className="flex items-center gap-1 rounded border border-[var(--nq-border)] px-2.5 py-1 text-xs text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)] hover:border-[var(--nq-border-hover)] transition-colors"
                >
                  <span>Indicators ({Object.values(activeIndicators).filter(Boolean).length})</span>
                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                </button>
                {indicatorsDropdownOpen && (
                  <div className="absolute right-0 top-full z-[100] mt-1 w-52 max-h-[380px] overflow-y-auto rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-2 shadow-lg ds-scrollable">
                    <p className="text-[9px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold border-b border-[var(--nq-border)] pb-1 mb-1">Overlays</p>
                    {([
                      ["ema9", "EMA 9"],
                      ["ema21", "EMA 21"],
                      ["ema50", "EMA 50"],
                      ["ema200", "EMA 200"],
                      ["sma20", "SMA 20"],
                      ["sma50", "SMA 50"],
                      ["sma100", "SMA 100"],
                      ["bollingerBands", "Bollinger Bands"],
                      ["superTrend", "SuperTrend"],
                      ["ichimoku", "Ichimoku Cloud"],
                      ["vwap", "VWAP"],
                    ] as const).map(([key, label]) => (
                      <label key={key} className="flex items-center gap-2 cursor-pointer rounded px-1.5 py-0.5 hover:bg-[rgba(255,255,255,0.05)] text-[10px] text-[var(--nq-text-secondary)] select-none">
                        <input type="checkbox" checked={activeIndicators[key]} onChange={() => setActiveIndicators((prev) => ({ ...prev, [key]: !prev[key] }))} className="rounded border-[var(--nq-border)] text-[var(--nq-accent-cyan)] focus:ring-0 bg-transparent h-3 w-3" />
                        <span className={activeIndicators[key] ? "text-[var(--nq-text-primary)] font-medium" : ""}>{label}</span>
                      </label>
                    ))}
                    <p className="text-[9px] uppercase tracking-wider text-[var(--nq-text-muted)] font-semibold border-b border-[var(--nq-border)] pb-0.5 mb-1 mt-2">Analysis & Oscillators</p>
                    {([
                      ["patterns", "Pattern Detector"],
                      ["rsi", "RSI (14)"],
                      ["macd", "MACD"],
                      ["atr", "ATR (14)"],
                      ["smc", "Smart Money Concepts"],
                    ] as const).map(([key, label]) => (
                      <label key={key} className="flex items-center gap-2 cursor-pointer rounded px-1.5 py-0.5 hover:bg-[rgba(255,255,255,0.05)] text-[10px] text-[var(--nq-text-secondary)] select-none">
                        <input type="checkbox" checked={activeIndicators[key]} onChange={() => setActiveIndicators((prev) => ({ ...prev, [key]: !prev[key] }))} className="rounded border-[var(--nq-border)] text-[var(--nq-accent-cyan)] focus:ring-0 bg-transparent h-3 w-3" />
                        <span className={activeIndicators[key] ? "text-[var(--nq-text-primary)] font-medium" : ""}>{label}</span>
                      </label>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          <div
            style={{ minHeight: `${chartHeight}px` }}
            className="relative rounded bg-[rgba(255,255,255,0.03)] p-2 w-full flex items-center justify-center"
          >
            {chartLoading ? (
              <div className="w-full flex flex-col gap-2 p-1" style={{ height: `${chartHeight}px` }}>
                <Skeleton className="h-full w-full rounded" />
              </div>
            ) : chartBars.length > 0 ? (
              <LightweightCandlestickChart
                bars={chartBars}
                chartStyle={chartStyle}
                height={chartHeight}
                symbol={symbol}
                liveTick={liveTick}
                indicators={activeIndicators}
                predictions={predictions}
              />
            ) : (
              <div className="flex h-full items-center justify-center p-4 text-center text-sm text-[var(--nq-text-secondary)]">
                No candlestick history available for {symbol}.
              </div>
            )}
          </div>
        </ChartCard>

        <article className="space-y-3">
          <ChartCard title="Signal Summary">
            <div className="space-y-3">
              <div className={`flex items-center gap-2 rounded border px-3 py-2 text-sm font-semibold uppercase tracking-wider ${badgeClass}`}>
                <span className={`h-2 w-2 rounded-full ${dotColor} ${isPulsing ? "animate-pulse" : ""}`} />
                <span>{signalDirection.replace("_", " ")}</span>
              </div>
              
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="rounded border border-[var(--nq-border)] p-2">
                  <p className="text-[var(--nq-text-secondary)]">Buy Prob</p>
                  <p className="font-semibold font-mono mt-0.5">
                    {signal?.prob_buy != null ? `${(Number(signal.prob_buy) * 100).toFixed(1)}%` : "—"}
                  </p>
                </div>
                <div className="rounded border border-[var(--nq-border)] p-2">
                  <p className="text-[var(--nq-text-secondary)]">Sell Prob</p>
                  <p className="font-semibold font-mono mt-0.5">
                    {signal?.prob_sell != null ? `${(Number(signal.prob_sell) * 100).toFixed(1)}%` : "—"}
                  </p>
                </div>
                <div className="rounded border border-[var(--nq-border)] p-2">
                  <p className="text-[var(--nq-text-secondary)]">5D Target</p>
                  <p className="font-semibold font-mono mt-0.5">₹{formatInr(signal?.target_price_5d)}</p>
                </div>
                <div className="rounded border border-[var(--nq-border)] p-2">
                  <p className="text-[var(--nq-text-secondary)]">Stop Loss</p>
                  <p className="font-semibold font-mono mt-0.5">₹{formatInr(signal?.stop_loss)}</p>
                </div>
                <div className="rounded border border-[var(--nq-border)] p-2">
                  <p className="text-[var(--nq-text-secondary)]">Kelly Size</p>
                  <p className="font-semibold font-mono mt-0.5">{(Number(signal?.ensemble.kelly_fraction ?? 0) * 100).toFixed(1)}%</p>
                </div>
                <div className="rounded border border-[var(--nq-border)] p-2">
                  <p className="text-[var(--nq-text-secondary)]">Regime</p>
                  <p className="font-semibold mt-0.5">{signal?.regime.state ?? "--"}</p>
                </div>
              </div>
            </div>
          </ChartCard>

          <ChartCard title="Model Grid">
            {predictionError ? (
              <div className="flex h-full flex-col items-center justify-center space-y-2 py-4">
                <div className="rounded border border-[rgba(255,193,7,0.35)] bg-[rgba(255,193,7,0.08)] px-3 py-1.5 text-xs text-[#F7C948] text-center font-medium">
                  Prediction model not yet trained
                </div>
                <p className="text-[10px] text-[var(--nq-text-secondary)] text-center max-w-[200px]">
                  Models are currently being trained in the backend. Predictions will appear here once ready.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="rounded border border-[var(--nq-border)] px-2 py-1">Latest model: {prediction?.model_name ?? "--"}</div>
                <div className="rounded border border-[var(--nq-border)] px-2 py-1">Predicted: {formatInr(prediction?.predicted_price)}</div>
                <div className="rounded border border-[var(--nq-border)] px-2 py-1">Consensus: {ensemble?.consensus_direction ?? "--"}</div>
                <div className="rounded border border-[var(--nq-border)] px-2 py-1">Confidence: {ensemble ? ensemble.consensus_confidence.toFixed(2) : "--"}</div>
              </div>
            )}
          </ChartCard>

          <ChartCard title="AI/ML Forecast" subtitle="Multi-horizon SARIMAX predictions">
            {predictions.length > 0 ? (
              <div className="space-y-1.5">
                {predictions.slice(0, 6).map((p, i) => {
                  const horizonLabel = p.target_date;
                  const price = p.predicted_price;
                  const low = p.prediction_low;
                  const high = p.prediction_high;
                  const isUp = latestPrice ? price > latestPrice : false;
                  return (
                    <div key={i} className="flex items-center justify-between rounded border border-[var(--nq-border)] px-2 py-1.5 text-xs">
                      <span className="text-[var(--nq-text-secondary)] font-mono text-[10px]">{horizonLabel}</span>
                      <div className="flex items-center gap-2">
                        {low != null && high != null && (
                          <span className="text-[9px] text-[var(--nq-text-muted)]">{formatInr(low)} – {formatInr(high)}</span>
                        )}
                        <span className={`font-semibold font-mono ${isUp ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
                          {isUp ? "▲" : "▼"} ₹{formatInr(price)}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-3 text-center text-xs text-[var(--nq-text-secondary)]">
                {forecastError ?? "Loading forecast..."}
              </div>
            )}
          </ChartCard>

          <ChartCard title="Model Breakdown" subtitle="Individual AI model signals">
            {signal?.models ? (
              <div className="space-y-1.5">
                {Object.entries(signal.models).map(([name, model]: [string, any]) => {
                  const dir = model?.direction ?? model?.signal ?? "NEUTRAL";
                  const conf = model?.confidence ?? model?.score ?? 0;
                  const isGreen = dir === "BUY" || dir === "STRONG_BUY" || dir === "BULLISH";
                  const isRed = dir === "SELL" || dir === "STRONG_SELL" || dir === "BEARISH";
                  return (
                    <div key={name} className="flex items-center justify-between rounded border border-[var(--nq-border)] px-2 py-1.5 text-xs">
                      <span className="text-[var(--nq-text-secondary)] capitalize">{name.replace(/_/g, " ")}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 rounded-full bg-[rgba(255,255,255,0.05)] overflow-hidden">
                          <div
                            className={`h-full rounded-full ${isGreen ? "bg-[#00E676]" : isRed ? "bg-[#FF3B5C]" : "bg-[#FFB800]"}`}
                            style={{ width: `${Math.min(100, Math.abs(Number(conf)) * 100)}%` }}
                          />
                        </div>
                        <span className={`font-semibold text-[10px] ${isGreen ? "text-[#00E676]" : isRed ? "text-[#FF3B5C]" : "text-[#FFB800]"}`}>
                          {dir}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-3 text-center text-xs text-[var(--nq-text-secondary)]">Loading model signals...</div>
            )}
          </ChartCard>

          <div className="rounded border border-red-500/20 bg-red-500/5 p-3 text-[11px] text-[var(--nq-text-secondary)] leading-relaxed space-y-1">
            <p className="font-semibold text-red-400">DISCLAIMER & RISK WARNING</p>
            <p>
              All system outputs, signals, and predictions are generated probabilistically by AI/ML models for research and educational purposes only. They carry no accuracy guarantee, do not constitute financial advice, and should not be used as the sole basis for real-world trading.
            </p>
          </div>
        </article>
      </section>

      <section className="relative z-10 mt-6 grid gap-4 xl:grid-cols-3">
        <ChartCard title="Quote Contract">
          <div className="space-y-2 text-xs">
            {[
              ["Open", formatInr(quote?.open)],
              ["High", formatInr(quote?.high)],
              ["Low", formatInr(quote?.low)],
              ["Previous Close", formatInr(quote?.previous_close)],
              ["Volume", quote ? quote.volume.toLocaleString("en-IN") : "--"],
            ].map(([key, value]) => (
              <div key={String(key)} className="flex items-center justify-between rounded bg-[rgba(255,255,255,0.02)] px-2 py-1">
                <span>{key}</span>
                <span>{value}</span>
              </div>
            ))}
          </div>
        </ChartCard>

        <ChartCard title="Regime + Weights" subtitle="Top model weights from ensemble stack">
          <div className="grid gap-3 lg:grid-cols-[1fr_120px]">
            <div className="space-y-2 text-xs text-[var(--nq-text-secondary)]">
              <div className="rounded border border-[var(--nq-border)] px-2 py-2">Regime: {signal?.regime.state ?? "--"}</div>
              <div className="rounded border border-[var(--nq-border)] px-2 py-2">Kelly: {signal ? signal.ensemble.kelly_fraction.toFixed(3) : "--"}</div>
              <div className="rounded border border-[var(--nq-border)] px-2 py-2">Models: {signal ? Object.keys(signal.model_weights).length : 0}</div>
            </div>
            <div className="h-[120px]">
              <SimpleDonutChart
                data={modelWeightSlices.length > 0 ? modelWeightSlices : [{ name: "No Data", value: 1, color: "var(--nq-border)" }]}
                centerLabel="Weights"
              />
            </div>
          </div>
        </ChartCard>

        <ChartCard title="Top Ensemble Models" subtitle="Weight concentration across model family">
          <div className="h-[180px]">
            {ensembleBars.length > 0 ? (
              <SimpleBarChart data={ensembleBars} yTickFormatter={(value) => value.toFixed(2)} />
            ) : (
              <div className="rounded bg-[rgba(255,255,255,0.02)] px-2 py-1 text-xs">No model data</div>
            )}
          </div>
        </ChartCard>
      </section>

      <section className="relative z-10 mt-6 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
        <div className="mb-4 flex flex-wrap items-center gap-2 border-b border-[var(--nq-border)] pb-3">
          {[
            { key: "fundamentals", label: "Fundamentals" },
            { key: "analysis", label: "Analysis" },
            { key: "similar", label: "Similar" },
          ].map((tab) => (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key as "fundamentals" | "analysis" | "similar")}
              className={`rounded border px-3 py-1.5 text-xs ${activeTab === tab.key ? "border-[var(--nq-accent-cyan)] bg-[rgba(0,212,245,0.12)] text-[var(--nq-text-primary)]" : "border-[var(--nq-border)] text-[var(--nq-text-secondary)] hover:border-[var(--nq-border-hover)]"}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === "fundamentals" ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {[
              ["Market Cap", derivedFundamentals.marketCap ? `₹${formatInr(derivedFundamentals.marketCap)}` : "--"],
              ["P/E", derivedFundamentals.pe?.toFixed(2) ?? "Provider required"],
              ["P/B", derivedFundamentals.pb?.toFixed(2) ?? "Provider required"],
              ["EPS", derivedFundamentals.eps ? `₹${formatInr(derivedFundamentals.eps)}` : "Provider required"],
              ["EV/EBITDA", derivedFundamentals.evEbitda?.toFixed(2) ?? "Provider required"],
              ["Net Margin", derivedFundamentals.netMargin !== null ? formatPercent(derivedFundamentals.netMargin) : "Provider required"],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-3 py-2 text-xs">
                <p className="text-[var(--nq-text-secondary)]">{label}</p>
                <p className="mt-1 text-sm font-semibold">{value}</p>
              </div>
            ))}
          </div>
        ) : null}

        {activeTab === "analysis" ? (
          <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
            <ChartCard title="SHAP Waterfall (Top Features)">
              <div className="h-[180px] rounded bg-[rgba(255,255,255,0.02)] p-2">
                {shapBars.length > 0 ? <SimpleBarChart data={shapBars} /> : <div className="px-2 py-1 text-xs text-[var(--nq-text-secondary)]">No SHAP data yet.</div>}
              </div>
            </ChartCard>

            <ChartCard title="Attention Heatmap" subtitle="Heads x recent timesteps">
              <div className="grid grid-cols-12 gap-1">
                {attentionHeatCells.length > 0 ? (
                  attentionHeatCells.map((cell) => (
                    <div
                      key={`a-${cell.headIndex}-${cell.stepIndex}`}
                      className="h-5 rounded"
                      style={{ background: `rgba(255,184,0,${0.1 + Math.min(0.75, cell.value * 3.2)})` }}
                    />
                  ))
                ) : (
                  <div className="col-span-12 py-4 text-center text-xs text-[var(--nq-text-secondary)] animate-pulse">
                    Computing attention weights...
                  </div>
                )}
              </div>
            </ChartCard>

            <ChartCard title="Counterfactual Panel" subtitle="Feature shifts to flip to BUY" className="xl:col-span-2">
              <div className="grid gap-3 md:grid-cols-3">
                {counterfactuals.length > 0 ? (
                  counterfactuals.slice(0, 3).map((cf) => (
                    <div key={cf.cf_id} className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] p-3">
                      <div className="mb-2 text-xs font-semibold text-[var(--nq-text-secondary)] flex justify-between">
                        <span>Path to {cf.resulting_signal}</span>
                        <span className="text-[var(--nq-text-tertiary)]">Score: {Number(cf.proximity_score).toFixed(2)}</span>
                      </div>
                      <div className="space-y-1">
                        {cf.changed_features.map((feat, idx) => (
                          <div key={idx} className="flex justify-between text-xs">
                            <span className="truncate w-24 text-[var(--nq-text-primary)]" title={feat.name}>{feat.name}</span>
                            <span className="text-[var(--nq-text-secondary)]">
                              {Number(feat.original).toFixed(2)} <span className="text-[var(--nq-text-tertiary)]">→</span> <span className="text-[var(--nq-accent-cyan)]">{Number(feat.counterfactual).toFixed(2)}</span>
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="col-span-3 py-4 text-center text-xs text-[var(--nq-text-secondary)] animate-pulse">
                    Computing optimal paths...
                  </div>
                )}
              </div>
            </ChartCard>
          </div>
        ) : null}

        {activeTab === "similar" ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {similarAssets.map((asset) => (
              <Link
                key={asset.ticker}
                href={`/markets/stocks/${encodeURIComponent(asset.ticker)}`}
                className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] p-3 text-xs transition hover:border-[var(--nq-accent-cyan)]"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold">{asset.ticker}</span>
                  <span className={asset.change_pct >= 0 ? "text-[var(--nq-accent-green)]" : "text-[var(--nq-accent-red)]"}>{formatPercent(asset.change_pct)}</span>
                </div>
                <p className="mt-1 truncate text-[var(--nq-text-secondary)]">{asset.name}</p>
                <p className="mt-2 text-[var(--nq-text-secondary)]">Signal {asset.signal_direction} | {(asset.confidence * 100).toFixed(1)}%</p>
              </Link>
            ))}
            {similarAssets.length === 0 ? <p className="text-xs text-[var(--nq-text-secondary)]">No similar assets available.</p> : null}
          </div>
        ) : null}
      </section>
    </main>
  );
}
