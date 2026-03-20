"use client";

import { useEffect, useMemo, useState } from "react";
import { intelligenceApi } from "@/lib/intelligence-api";
import { marketApi, predictionsApi } from "@/lib/api-client";
import { usePriceFeed } from "@/hooks/usePriceFeed";
import { AmbientLucideBackground } from "@/components/common/ambient-lucide-background";
import type { HistoryResponse, ModelEnsemble, Prediction, Quote } from "@neuroquant/types";
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
  const [quote, setQuote] = useState<Quote | null>(null);
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [ensemble, setEnsemble] = useState<ModelEnsemble | null>(null);
  const [signal, setSignal] = useState<SignalResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const { ticks, status } = usePriceFeed([symbol]);
  const liveTick = ticks.get(symbol.toUpperCase());

  useEffect(() => {
    let isMounted = true;

    async function load(): Promise<void> {
      setIsLoading(true);
      setError(null);

      const [quoteResult, historyResult, predictionResult, ensembleResult, signalResult] = await Promise.allSettled([
        marketApi.getQuote(symbol),
        marketApi.getHistory(symbol, "1D"),
        predictionsApi.getLatest(symbol),
        predictionsApi.getEnsemble(symbol),
        intelligenceApi.getSignal(symbol),
      ]);

      if (!isMounted) {
        return;
      }

      if (quoteResult.status === "fulfilled") {
        setQuote(quoteResult.value);
      } else {
        setError("Unable to load market quote contract.");
      }

      if (historyResult.status === "fulfilled") {
        setHistory(historyResult.value);
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

      setIsLoading(false);
    }

    void load();

    return () => {
      isMounted = false;
    };
  }, [symbol]);

  const latestPrice = liveTick?.price ?? quote?.price;
  const latestChangePct = liveTick?.change_pct ?? quote?.change_percent;

  const historyHeights = useMemo(() => {
    const closes = history?.bars.map((bar) => bar.close) ?? [];
    if (closes.length === 0) {
      return [] as number[];
    }
    const min = Math.min(...closes);
    const max = Math.max(...closes);
    const range = Math.max(max - min, 1e-9);
    return closes.slice(-120).map((close) => 8 + ((close - min) / range) * 84);
  }, [history]);

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
        <article className="rounded-lg border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Price History ({history?.interval ?? "1D"})</h2>
          <div className="h-[280px] rounded bg-[rgba(255,255,255,0.03)] p-2 sm:h-[340px] lg:h-[360px]">
            <div className="flex h-full items-end gap-[2px]">
              {(isLoading ? Array.from({ length: 90 }, () => 20) : historyHeights).map((height, index) => (
                <div key={`bar-${index}`} className="w-full rounded-sm bg-[var(--nq-accent-cyan)]/48" style={{ height: `${height}%` }} />
              ))}
            </div>
          </div>
        </article>

        <article className="space-y-3">
          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
            <h3 className="mb-2 text-sm font-medium text-[var(--nq-text-secondary)]">Signal Summary</h3>
            <div className="rounded border border-[rgba(0,230,118,0.4)] bg-[rgba(0,230,118,0.08)] px-3 py-2 text-sm font-semibold text-[var(--nq-accent-green)]">
              {signal?.ensemble.signal ?? "--"} | Confidence {signal ? signal.ensemble.confidence.toFixed(2) : "--"}
            </div>
          </div>

          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
            <h3 className="mb-2 text-sm font-medium text-[var(--nq-text-secondary)]">Model Grid</h3>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="rounded border border-[var(--nq-border)] px-2 py-1">Latest model: {prediction?.model_name ?? "--"}</div>
              <div className="rounded border border-[var(--nq-border)] px-2 py-1">Predicted: {formatInr(prediction?.predicted_price)}</div>
              <div className="rounded border border-[var(--nq-border)] px-2 py-1">Consensus: {ensemble?.consensus_direction ?? "--"}</div>
              <div className="rounded border border-[var(--nq-border)] px-2 py-1">Confidence: {ensemble ? ensemble.consensus_confidence.toFixed(2) : "--"}</div>
            </div>
          </div>
        </article>
      </section>

      <section className="relative z-10 mt-6 grid gap-4 xl:grid-cols-3">
        <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h2 className="mb-2 text-sm font-medium text-[var(--nq-text-secondary)]">Quote Contract</h2>
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
        </article>

        <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h2 className="mb-2 text-sm font-medium text-[var(--nq-text-secondary)]">Regime + Weights</h2>
          <div className="space-y-2 text-xs text-[var(--nq-text-secondary)]">
            <div className="rounded border border-[var(--nq-border)] px-2 py-2">Regime: {signal?.regime.state ?? "--"}</div>
            <div className="rounded border border-[var(--nq-border)] px-2 py-2">Kelly: {signal ? signal.ensemble.kelly_fraction.toFixed(3) : "--"}</div>
            <div className="rounded border border-[var(--nq-border)] px-2 py-2">Models: {signal ? Object.keys(signal.model_weights).length : 0}</div>
          </div>
        </article>

        <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h2 className="mb-2 text-sm font-medium text-[var(--nq-text-secondary)]">Top Ensemble Models</h2>
          <div className="space-y-2 text-xs">
            {(ensemble?.models ?? []).slice(0, 6).map((model) => (
              <div key={model.name} className="flex items-center justify-between rounded bg-[rgba(255,255,255,0.02)] px-2 py-1">
                <span>{model.name}</span>
                <span>{model.weight.toFixed(3)}</span>
              </div>
            ))}
            {!ensemble || ensemble.models.length === 0 ? <div className="rounded bg-[rgba(255,255,255,0.02)] px-2 py-1">No model data</div> : null}
          </div>
        </article>
      </section>
    </main>
  );
}
