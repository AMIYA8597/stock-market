"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { contractsApi, type MarketMover } from "@/lib/contracts-api";
import { usePriceFeed } from "@/hooks/usePriceFeed";

export default function StocksUniversePage(): JSX.Element {
  const [symbols, setSymbols] = useState<MarketMover[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);

      try {
        const movers = await contractsApi.getMovers("NSE", "momentum");
        if (!mounted) {
          return;
        }
        setSymbols(movers);
      } catch {
        if (!mounted) {
          return;
        }
        setError("Unable to load stocks universe contract.");
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

  const trackedSymbols = useMemo(() => symbols.map((item) => item.ticker.toUpperCase()), [symbols]);
  const { ticks, status } = usePriceFeed(trackedSymbols);

  return (
    <main className="min-h-screen bg-[var(--nq-bg-base)] px-4 py-6 text-[var(--nq-text-primary)] sm:px-6 sm:py-8">
      <h1 className="text-2xl font-semibold">Stocks Universe</h1>
      <p className="mt-2 text-sm text-[var(--nq-text-secondary)]">Core watch universe for institutional signal workflows. WS: {status}</p>
      {error ? <p className="mt-2 text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <div className="mt-6 rounded-lg border border-[var(--nq-border)] bg-[var(--nq-bg-card)]">
        <div className="hidden grid-cols-[1.5fr_1fr_1fr_1fr_1fr] px-4 py-2 text-xs text-[var(--nq-text-secondary)] lg:grid">
          <span>Symbol</span>
          <span>Exchange</span>
          <span className="text-right">Price</span>
          <span className="text-right">Move</span>
          <span className="text-right">Signal</span>
        </div>

        {symbols.map((item) => {
          const live = ticks.get(item.ticker.toUpperCase());
          const livePrice = live?.price ?? item.price;
          const liveChange = live?.change_pct ?? item.change_pct;
          const changeColor = liveChange >= 0 ? 'text-[#00E676]' : 'text-[#FF3B5C]';

          return (
            <Link
              key={item.ticker}
              href={`/markets/stocks/${encodeURIComponent(item.ticker)}`}
              className="border-t border-[var(--nq-border)] px-4 py-3 text-sm hover:bg-[rgba(255,255,255,0.03)]"
            >
              <div className="grid gap-2 lg:grid-cols-[1.5fr_1fr_1fr_1fr_1fr] lg:items-center">
                <div>
                  <span className="font-medium">{item.ticker}</span>
                  <p className="mt-0.5 text-xs text-[var(--nq-text-secondary)] lg:hidden">{item.name}</p>
                </div>
                <span className="hidden text-[var(--nq-text-secondary)] lg:block">{item.exchange}</span>
                <span className="lg:text-right">{livePrice.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span>
                <span className={`lg:text-right ${changeColor}`}>{liveChange >= 0 ? "+" : ""}{liveChange.toFixed(2)}%</span>
                <div className="flex items-center justify-between lg:justify-end">
                  <span className="text-xs text-[var(--nq-text-secondary)] lg:hidden">Signal</span>
                  <span>{item.signal_direction}</span>
                </div>
              </div>
            </Link>
          );
        })}
        {loading
          ? Array.from({ length: 8 }, (_, i) => (
              <div key={`skeleton-row-${i}`} className="border-t border-[var(--nq-border)] px-4 py-3 text-sm">
                <div className="grid gap-2 lg:grid-cols-[1.5fr_1fr_1fr_1fr_1fr] lg:items-center">
                  <span className="h-3 w-24 rounded bg-[rgba(255,255,255,0.10)]" />
                  <span className="h-3 w-16 rounded bg-[rgba(255,255,255,0.10)]" />
                  <span className="h-3 w-20 rounded bg-[rgba(255,255,255,0.10)] lg:ml-auto" />
                  <span className="h-3 w-14 rounded bg-[rgba(255,255,255,0.10)] lg:ml-auto" />
                  <span className="h-3 w-16 rounded bg-[rgba(255,255,255,0.10)] lg:ml-auto" />
                </div>
              </div>
            ))
          : null}
      </div>
    </main>
  );
}
