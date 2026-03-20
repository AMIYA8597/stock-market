"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { contractsApi, type MarketIndex, type MarketMover } from "@/lib/contracts-api";
import { usePriceFeed } from "@/hooks/usePriceFeed";

const sections = [
  {
    title: "Stocks",
    description: "Universe view, sector heatmaps, and full symbol drill-down.",
    href: "/markets/stocks",
  },
  {
    title: "Crypto",
    description: "Spot market monitoring and model-driven coin intelligence.",
    href: "/markets/crypto",
  },
  {
    title: "Forex",
    description: "Major FX pairs with macro and volatility overlays.",
    href: "/markets/forex",
  },
];

export default function MarketsPage(): JSX.Element {
  const [indices, setIndices] = useState<MarketIndex[]>([]);
  const [movers, setMovers] = useState<MarketMover[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);

      const [indicesRes, moversRes] = await Promise.allSettled([
        contractsApi.getIndices(),
        contractsApi.getMovers("NSE", "momentum"),
      ]);

      if (!mounted) {
        return;
      }

      if (indicesRes.status === "fulfilled") {
        setIndices(indicesRes.value);
      } else {
        setError("Unable to load market indices contract.");
      }

      if (moversRes.status === "fulfilled") {
        setMovers(moversRes.value);
      }

      setLoading(false);
    }

    void load();

    return () => {
      mounted = false;
    };
  }, []);

  const liveSymbols = useMemo(() => movers.map((item) => item.ticker), [movers]);
  const { ticks, status } = usePriceFeed(liveSymbols);

  return (
    <main className="min-h-screen bg-[var(--nq-bg-base)] p-8 text-[var(--nq-text-primary)]">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Markets Overview</h1>
          <p className="mt-2 text-sm text-[var(--nq-text-secondary)]">Choose a market module to launch analytics views.</p>
        </div>
        <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1 text-xs text-[var(--nq-text-secondary)]">
          Live contracts + ws: {status}
        </div>
      </div>

      {error ? <p className="mt-3 text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <section className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {(loading ? [] : indices.slice(0, 4)).map((indexItem) => (
          <div key={indexItem.ticker} className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3">
            <div className="text-xs text-[var(--nq-text-secondary)]">{indexItem.name}</div>
            <div className="mt-1 text-sm font-semibold">{indexItem.value.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</div>
            <div className="mt-1 text-xs">{indexItem.change_pct >= 0 ? "+" : ""}{indexItem.change_pct.toFixed(2)}%</div>
          </div>
        ))}
        {loading
          ? Array.from({ length: 4 }, (_, i) => (
              <div key={`index-skeleton-${i}`} className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3">
                <div className="h-3 w-24 rounded bg-[rgba(255,255,255,0.12)]" />
                <div className="mt-2 h-4 w-20 rounded bg-[rgba(255,255,255,0.12)]" />
                <div className="mt-2 h-3 w-16 rounded bg-[rgba(255,255,255,0.10)]" />
              </div>
            ))
          : null}
      </section>

      <section className="mt-5 rounded-lg border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
        <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Momentum Movers (NSE)</h2>
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {movers.slice(0, 6).map((item) => {
            const live = ticks.get(item.ticker.toUpperCase());
            const livePrice = live?.price ?? item.price;
            const liveChange = live?.change_pct ?? item.change_pct;
            return (
              <Link
                key={item.ticker}
                href={`/markets/stocks/${encodeURIComponent(item.ticker)}`}
                className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] p-3 text-sm hover:bg-[rgba(255,255,255,0.04)]"
              >
                <div className="flex items-center justify-between">
                  <span>{item.ticker}</span>
                  <span className="text-xs">{item.signal_direction}</span>
                </div>
                <div className="mt-1 text-xs text-[var(--nq-text-secondary)]">{item.name}</div>
                <div className="mt-2 flex items-center justify-between text-xs">
                  <span>{livePrice.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span>
                  <span>{liveChange >= 0 ? "+" : ""}{liveChange.toFixed(2)}%</span>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      <section className="mt-8 grid gap-4 md:grid-cols-3">
        {sections.map((item) => (
          <Link
            key={item.title}
            href={item.href}
            className="rounded-lg border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-5 transition hover:border-[var(--nq-accent-cyan)]"
          >
            <h2 className="text-lg font-medium">{item.title}</h2>
            <p className="mt-2 text-sm text-[var(--nq-text-secondary)]">{item.description}</p>
          </Link>
        ))}
      </section>
    </main>
  );
}
