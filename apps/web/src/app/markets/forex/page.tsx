"use client";

import { useEffect, useMemo, useState } from "react";
import { marketApi } from "@/lib/api-client";
import { usePriceFeed } from "@/hooks/usePriceFeed";
import { AmbientLucideBackground } from "@/components/common/ambient-lucide-background";
import type { Quote } from "@neuroquant/types";

const pairs = ["EURUSD", "GBPUSD", "USDJPY", "USDINR", "EURINR"];

export default function ForexPage(): JSX.Element {
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);
      try {
        const data = await marketApi.getQuotes(pairs);
        if (!mounted) {
          return;
        }
        setQuotes(data);
      } catch {
        if (!mounted) {
          return;
        }
        setError("Unable to load forex quotes contract.");
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      mounted = false;
    };
  }, []);

  const symbols = useMemo(() => pairs.map((pair) => pair.toUpperCase()), []);
  const { ticks, status } = usePriceFeed(symbols);

  return (
    <main className="relative min-h-screen overflow-hidden bg-[var(--nq-bg-base)] px-4 py-6 text-[var(--nq-text-primary)] sm:px-6 lg:px-8">
      <AmbientLucideBackground className="opacity-75" />
      <h1 className="relative z-10 text-2xl font-semibold">Forex Dashboard</h1>
      <p className="relative z-10 mt-2 text-sm text-[var(--nq-text-secondary)]">Major FX pairs with macro and volatility overlays. WS: {status}</p>
      {error ? <p className="mt-2 text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <div className="relative z-10 mt-6 grid gap-2 sm:grid-cols-2 md:grid-cols-3">
        {pairs.map((pair, idx) => {
          const quote = quotes.find((item) => item.symbol.toUpperCase() === pair.toUpperCase());
          const live = ticks.get(pair.toUpperCase());
          const spot = live?.price ?? quote?.price ?? (1.01 + idx * 0.13);
          const move = live?.change_pct ?? quote?.change_percent ?? (idx % 2 === 0 ? 0.08 + idx * 0.04 : -(0.08 + idx * 0.04));

          return (
            <div key={pair} className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3 text-sm">
              <div className="font-medium">{pair}</div>
              <div className="mt-1 text-xs text-[var(--nq-text-secondary)]">Spot {spot.toFixed(4)}</div>
              <div className="mt-1 text-xs">Move {move >= 0 ? "+" : ""}{move.toFixed(2)}%</div>
            </div>
          );
        })}
        {loading
          ? Array.from({ length: 2 }, (_, i) => (
              <div key={`fx-skeleton-${i}`} className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3 text-sm">
                <div className="h-3 w-20 rounded bg-[rgba(255,255,255,0.10)]" />
                <div className="mt-2 h-3 w-24 rounded bg-[rgba(255,255,255,0.08)]" />
                <div className="mt-2 h-3 w-16 rounded bg-[rgba(255,255,255,0.10)]" />
              </div>
            ))
          : null}
      </div>

      <section className="relative z-10 mt-6 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
        <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Macro Overlay</h2>
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4 text-xs">
          {[
            ["US 10Y", "4.22%"],
            ["DXY", "103.8"],
            ["Crude", "$79.4"],
            ["VIX", "16.3"],
          ].map(([k, v]) => (
            <div key={k} className="rounded border border-[var(--nq-border)] px-3 py-2">
              <div className="text-[var(--nq-text-secondary)]">{k}</div>
              <div className="mt-1 font-semibold">{v}</div>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
