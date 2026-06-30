"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
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
  LightweightCandlestickChart,
} from "@/components/charts";
import { Skeleton } from "@/components/ui/Skeleton";
import { type PriceBar } from "@/utils/chartFormatters";
import type { ModelEnsemble, Prediction, Quote } from "@neuroquant/types";
import type { SignalResponse } from "@/types/intelligence";

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
  const [chartStyle, setChartStyle] = useState<"candlestick" | "heikin-ashi" | "line">("candlestick");
  const [chartHeight, setChartHeight] = useState<number>(360);

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
            const mapped: PriceBar[] = historyRes.bars.map((bar) => ({
              timestamp: bar.timestamp,
              open: Number(bar.open),
              high: Number(bar.high),
              low: Number(bar.low),
              close: Number(bar.close),
              volume: Number(bar.volume),
            }));
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
        <div className="grid w-full grid-cols-2 gap-2 text-xs sm:w-auto">
          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-2">Price {formatInr(latestPrice)}</div>
          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-2">Day {formatPercent(latestChangePct)}</div>
        </div>
      </div>

      <p className="relative z-10 mt-2 text-xs text-[var(--nq-text-secondary)]">WS status: {status}</p>
      {error ? <p className="mt-2 text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <section className="relative z-10 mt-6 grid gap-4 xl:grid-cols-[1fr_320px]">
        <ChartCard title={`Price History (${chartInterval.toUpperCase()})`} subtitle="Live interactive candlestick overlays">
          {/* Timeframe Selector and Chart Style controls */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--nq-border)] pb-3 mb-3">
            <div className="flex items-center gap-1 overflow-x-auto ds-scrollable py-1">
              {(["1m", "5m", "15m", "1h", "1d", "1w", "1mo"] as const).map((interval) => (
                <button
                  key={interval}
                  type="button"
                  onClick={() => setChartInterval(interval)}
                  className={`rounded border px-2.5 py-1 text-xs font-semibold font-mono transition-colors uppercase ${
                    chartInterval === interval
                      ? "border-[var(--nq-accent-cyan)] bg-[rgba(0,212,245,0.12)] text-[var(--nq-text-primary)]"
                      : "border-[var(--nq-border)] text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)] hover:border-[var(--nq-border-hover)]"
                  }`}
                >
                  {interval}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-1">
              {(["candlestick", "heikin-ashi", "line"] as const).map((style) => (
                <button
                  key={style}
                  type="button"
                  onClick={() => setChartStyle(style)}
                  className={`rounded border px-2.5 py-1 text-xs font-semibold transition-colors capitalize ${
                    chartStyle === style
                      ? "border-[var(--nq-accent-cyan)] bg-[rgba(0,212,245,0.12)] text-[var(--nq-text-primary)]"
                      : "border-[var(--nq-border)] text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)] hover:border-[var(--nq-border-hover)]"
                  }`}
                >
                  {style.replace("-", " ")}
                </button>
              ))}
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
                indicators={{
                  ema21: true,
                  ema50: true,
                  vwap: true,
                  rsi: true,
                  macd: true,
                  superTrend: true,
                  patterns: true,
                  smc: true,
                  bollingerBands: true,
                  atr: true,
                }}
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
                  <p className="font-semibold font-mono mt-0.5">{(Number(signal?.prob_buy ?? 0.5) * 100).toFixed(1)}%</p>
                </div>
                <div className="rounded border border-[var(--nq-border)] p-2">
                  <p className="text-[var(--nq-text-secondary)]">Sell Prob</p>
                  <p className="font-semibold font-mono mt-0.5">{(Number(signal?.prob_sell ?? 0.5) * 100).toFixed(1)}%</p>
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
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="rounded border border-[var(--nq-border)] px-2 py-1">Latest model: {prediction?.model_name ?? "--"}</div>
              <div className="rounded border border-[var(--nq-border)] px-2 py-1">Predicted: {formatInr(prediction?.predicted_price)}</div>
              <div className="rounded border border-[var(--nq-border)] px-2 py-1">Consensus: {ensemble?.consensus_direction ?? "--"}</div>
              <div className="rounded border border-[var(--nq-border)] px-2 py-1">Confidence: {ensemble ? ensemble.consensus_confidence.toFixed(2) : "--"}</div>
            </div>
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
                {(attentionHeatCells.length > 0
                  ? attentionHeatCells
                  : Array.from({ length: 96 }, (_, idx) => ({
                      headIndex: Math.floor(idx / 12),
                      stepIndex: idx % 12,
                      value: 0.05,
                    }))
                ).map((cell) => (
                  <div
                    key={`a-${cell.headIndex}-${cell.stepIndex}`}
                    className="h-5 rounded"
                    style={{ background: `rgba(255,184,0,${0.1 + Math.min(0.75, cell.value * 3.2)})` }}
                  />
                ))}
              </div>
            </ChartCard>

            <ChartCard title="Counterfactual Panel" subtitle="Feature shifts to flip to BUY" className="xl:col-span-2">
              <div className="grid gap-3 md:grid-cols-3">
                {(counterfactuals.length > 0 ? counterfactuals : [{ cf_id: "CF1", changed_features: [], resulting_signal: "BUY", proximity_score: 0 }] as CounterfactualResponse[])
                  .slice(0, 3)
                  .map((cf) => (
                    <div key={cf.cf_id} className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] p-3 text-xs">
                      <p className="mb-2 font-semibold">{cf.cf_id}</p>
                      <div className="space-y-1">
                        {cf.changed_features.slice(0, 5).map((feature) => (
                          <div key={`${cf.cf_id}-${feature.name}`} className="flex items-center justify-between gap-2">
                            <span className="text-[var(--nq-text-secondary)]">{feature.name}</span>
                            <span>{feature.original.toFixed(2)} {'->'} {feature.counterfactual.toFixed(2)}</span>
                          </div>
                        ))}
                        {cf.changed_features.length === 0 ? <p className="text-[var(--nq-text-secondary)]">No counterfactual deltas available.</p> : null}
                      </div>
                    </div>
                  ))}
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
