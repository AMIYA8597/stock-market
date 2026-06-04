"use client";

import { useEffect, useMemo, useState } from "react";
import { intelligenceApi } from "@/lib/intelligence-api";
import { marketApi, predictionsApi } from "@/lib/api-client";
import { usePriceFeed } from "@/hooks/usePriceFeed";
import { AmbientLucideBackground } from "@/components/common/ambient-lucide-background";
import type { HistoryResponse, ModelEnsemble, Prediction, Quote } from "@neuroquant/types";
import type { SignalResponse } from "@/types/intelligence";

interface CryptoCoinLiveContentProps {
  coin: string;
}

interface RelatedAsset {
  ticker: string;
  name: string;
  correlation: number;
  signal: string;
  confidence: number;
}

function formatNumber(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return value.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function formatUSD(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  if (value >= 1e9) {
    return `$${(value / 1e9).toFixed(2)}B`;
  }
  if (value >= 1e6) {
    return `$${(value / 1e6).toFixed(2)}M`;
  }
  return `$${value.toFixed(0)}`;
}

function formatPct(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

export function CryptoCoinLiveContent({ coin }: CryptoCoinLiveContentProps): JSX.Element {
  const [quote, setQuote] = useState<Quote | null>(null);
  const [history, setHistory] = useState<HistoryResponse | null>(null);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [ensemble, setEnsemble] = useState<ModelEnsemble | null>(null);
  const [signal, setSignal] = useState<SignalResponse | null>(null);
  const [marketCap, setMarketCap] = useState<number | null>(null);
  const [volume24h, setVolume24h] = useState<number | null>(null);
  const [dominance, setDominance] = useState<number | null>(null);
  const [relatedAssets, setRelatedAssets] = useState<RelatedAsset[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const { ticks, status } = usePriceFeed([coin]);
  const liveTick = ticks.get(coin.toUpperCase());

  useEffect(() => {
    let mounted = true;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);

      const [quoteRes, historyRes, predictionRes, ensembleRes, signalRes] = await Promise.allSettled([
        marketApi.getQuote(coin),
        marketApi.getHistory(coin, "1D"),
        predictionsApi.getLatest(coin),
        predictionsApi.getEnsemble(coin),
        intelligenceApi.getSignal(coin),
      ]);

      if (!mounted) {
        return;
      }

      if (quoteRes.status === "fulfilled") {
        setQuote(quoteRes.value);
        setMarketCap(null);
        setVolume24h(null);
        setDominance(null);
        setRelatedAssets([]);
      } else {
        setError("Unable to load coin quote contract.");
      }
      if (historyRes.status === "fulfilled") {
        setHistory(historyRes.value);
      }
      if (predictionRes.status === "fulfilled") {
        setPrediction(predictionRes.value);
      }
      if (ensembleRes.status === "fulfilled") {
        setEnsemble(ensembleRes.value);
      }
      if (signalRes.status === "fulfilled") {
        setSignal(signalRes.value);
      }

      setLoading(false);
    }

    void load();

    return () => {
      mounted = false;
    };
  }, [coin]);

  const seriesBars = useMemo(() => {
    const closes = history?.bars.map((bar) => bar.close) ?? [];
    if (closes.length === 0) {
      return [] as number[];
    }
    const min = Math.min(...closes);
    const max = Math.max(...closes);
    const range = Math.max(max - min, 1e-9);
    return closes.slice(-120).map((close) => 10 + ((close - min) / range) * 85);
  }, [history]);

  const livePrice = liveTick?.price ?? quote?.price;
  const liveMove = liveTick?.change_pct ?? quote?.change_percent;

  return (
    <main className="relative min-h-screen overflow-hidden bg-[var(--nq-bg-base)] px-4 py-6 text-[var(--nq-text-primary)] sm:px-6 lg:px-8">
      <AmbientLucideBackground className="opacity-70" />
      <h1 className="relative z-10 text-2xl font-semibold">{coin}</h1>
      <p className="relative z-10 mt-2 text-sm text-[var(--nq-text-secondary)]">Coin detail page with signal overlays and volatility modules. WS: {status}</p>
      {error ? <p className="mt-2 text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <section className="relative z-10 mt-6 grid gap-4 xl:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          {/* Price + Volatility Chart */}
          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
            <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Price + Volatility</h2>
            <div className="mb-3 grid grid-cols-2 gap-2 text-xs">
              <div className="rounded border border-[var(--nq-border)] px-2 py-1">Price {formatNumber(livePrice)}</div>
              <div className="rounded border border-[var(--nq-border)] px-2 py-1">Move {formatPct(liveMove)}</div>
            </div>
            <div className="h-64 rounded bg-[rgba(255,255,255,0.03)] p-2 sm:h-72">
              <div className="flex h-full items-end gap-[2px]">
                {(loading ? Array.from({ length: 80 }, () => 20) : seriesBars).map((height, index) => (
                  <div key={`bar-${index}`} className="w-full rounded-sm bg-[var(--nq-accent-cyan)]/52" style={{ height: `${height}%` }} />
                ))}
              </div>
            </div>
          </div>

          {/* Market Metrics */}
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3">
              <div className="text-xs text-[var(--nq-text-secondary)]">Market Cap</div>
              <div className="mt-1 text-sm font-semibold">{loading ? "..." : formatUSD(marketCap)}</div>
            </div>
            <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3">
              <div className="text-xs text-[var(--nq-text-secondary)]">24h Volume</div>
              <div className="mt-1 text-sm font-semibold">{loading ? "..." : formatUSD(volume24h)}</div>
            </div>
            <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3">
              <div className="text-xs text-[var(--nq-text-secondary)]">Market Dominance</div>
              <div className="mt-1 text-sm font-semibold">{loading ? "..." : formatPct(dominance)}</div>
            </div>
          </div>

          {/* Trading Pair Depth */}
          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
            <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Order Book Depth</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <div className="mb-2 text-xs text-[var(--nq-accent-green)]">Bids (Buy Side)</div>
                <div className="space-y-1">
                  {[0.02, 0.015, 0.012, 0.008, 0.005].map((depth, idx) => (
                    <div key={`bid-${idx}`} className="flex items-center gap-2">
                      <div className="h-2 rounded bg-[var(--nq-accent-green)]/40" style={{ width: `${depth * 100}%` }} />
                      <span className="text-xs">${(livePrice ?? 0 * (1 - (idx + 1) * 0.002)).toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <div className="mb-2 text-xs text-[var(--nq-accent-red)]">Asks (Sell Side)</div>
                <div className="space-y-1">
                  {[0.02, 0.015, 0.012, 0.008, 0.005].map((depth, idx) => (
                    <div key={`ask-${idx}`} className="flex items-center gap-2">
                      <div className="h-2 rounded bg-[var(--nq-accent-red)]/40" style={{ width: `${depth * 100}%` }} />
                      <span className="text-xs">${(livePrice ?? 0 * (1 + (idx + 1) * 0.002)).toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Related Assets */}
          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
            <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Related Assets</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {relatedAssets.map((asset) => (
                <div key={asset.ticker} className="rounded border border-[var(--nq-border)]/50 bg-[rgba(255,255,255,0.02)] p-3 text-xs">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-semibold text-[var(--nq-text-primary)]">{asset.ticker}</div>
                      <div className="text-xs text-[var(--nq-text-secondary)]">{asset.name}</div>
                    </div>
                    <div
                      className={`rounded px-2 py-1 text-[10px] font-medium ${
                        asset.signal === "BUY"
                          ? "bg-[var(--nq-accent-green)]/20 text-[var(--nq-accent-green)]"
                          : asset.signal === "SELL"
                            ? "bg-[var(--nq-accent-red)]/20 text-[var(--nq-accent-red)]"
                            : "bg-[var(--nq-accent-amber)]/20 text-[var(--nq-accent-amber)]"
                      }`}
                    >
                      {asset.signal}
                    </div>
                  </div>
                  <div className="mt-2 space-y-1 pt-2 border-t border-[var(--nq-border)]/30">
                    <div className="flex items-center justify-between">
                      <span className="text-[var(--nq-text-secondary)]">Correlation</span>
                      <span className="font-semibold">{asset.correlation.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-[var(--nq-text-secondary)]">Confidence</span>
                      <span className="font-semibold">{(asset.confidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <aside className="space-y-3">
          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4 text-sm">
            <div className="text-xs text-[var(--nq-text-secondary)]">Ensemble Signal</div>
            <div className="mt-1 font-semibold text-[var(--nq-accent-green)]">
              {signal?.ensemble.signal ?? "--"} ({signal ? signal.ensemble.confidence.toFixed(2) : "--"})
            </div>
            <div className="mt-2 text-xs text-[var(--nq-text-secondary)]">Kelly: {signal ? signal.ensemble.kelly_fraction.toFixed(3) : "--"}</div>
          </div>
          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4 text-xs">
            <div className="mb-2 font-medium text-[var(--nq-text-secondary)]">Top Ensemble Models</div>
            <div className="space-y-1">
              {(ensemble?.models ?? []).slice(0, 5).map((item) => (
                <div key={item.name} className="flex items-center justify-between">
                  <span>{item.name}</span>
                  <span>{item.weight.toFixed(3)}</span>
                </div>
              ))}
              {!ensemble || ensemble.models.length === 0 ? <div className="text-[var(--nq-text-secondary)]">No model data</div> : null}
            </div>
          </div>
          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4 text-xs">
            <div className="mb-2 font-medium text-[var(--nq-text-secondary)]">Latest Prediction</div>
            <div className="space-y-1">
              <div className="flex items-center justify-between"><span>Model</span><span>{prediction?.model_name ?? "--"}</span></div>
              <div className="flex items-center justify-between"><span>Predicted Price</span><span>{formatNumber(prediction?.predicted_price)}</span></div>
              <div className="flex items-center justify-between"><span>Confidence</span><span>{prediction ? prediction.confidence.toFixed(2) : "--"}</span></div>
            </div>
          </div>
        </aside>
      </section>
    </main>
  );
}
