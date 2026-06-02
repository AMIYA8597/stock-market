"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { contractsApi, type MarketMover } from "@/lib/contracts-api";
import { usePriceFeed } from "@/hooks/usePriceFeed";
import { safeFormat } from "@/lib/formatters";

export default function CryptoPage(): JSX.Element {
  const [coins, setCoins] = useState<MarketMover[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let mounted = true;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);

      try {
        const movers = await contractsApi.getMovers("CRYPTO", "momentum");
        if (!mounted) {
          return;
        }
        setCoins(movers);
      } catch {
        if (!mounted) {
          return;
        }
        setError("Unable to load crypto contract.");
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

  const symbols = useMemo(() => coins.map((item) => item.ticker.toUpperCase()), [coins]);
  const { ticks, status } = usePriceFeed(symbols);

  const avgConfidence = useMemo(() => {
    if (coins.length === 0) {
      return 0;
    }
    const sum = coins.reduce((acc, item) => acc + Number(item.confidence || 0), 0);
    return sum / coins.length;
  }, [coins]);

  return (
    <main className="min-h-screen bg-[var(--nq-bg-base)] p-8 text-[var(--nq-text-primary)]">
      <h1 className="text-2xl font-semibold">Crypto Market</h1>
      <p className="mt-2 text-sm text-[var(--nq-text-secondary)]">Spot monitoring with signal overlays and volatility snapshots. WS: {status}</p>
      {error ? <p className="mt-2 text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <section className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Tracked Assets", String(coins.length)],
          ["Avg Confidence", `${safeFormat(avgConfidence * 100, 1)}%`],
          ["Top Signal", coins[0]?.signal_direction ?? "--"],
          ["Top Exchange", coins[0]?.exchange ?? "CRYPTO"],
        ].map(([k, v]) => (
          <div key={k} className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3 text-sm">
            <div className="text-xs text-[var(--nq-text-secondary)]">{k}</div>
            <div className="mt-1 font-semibold">{v}</div>
          </div>
        ))}
      </section>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {coins.slice(0, 8).map((coin) => {
          const live = ticks.get(coin.ticker.toUpperCase());
          const livePrice = live?.price ?? coin.price;
          const liveChange = live?.change_pct ?? coin.change_pct;
          return (
          <Link
            key={coin.ticker}
            href={`/markets/crypto/${encodeURIComponent(coin.ticker)}`}
            className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3 text-sm transition-colors hover:border-[var(--nq-accent-cyan)]"
          >
            <div className="flex items-center justify-between">
              <div className="font-medium">{coin.ticker}</div>
              <div className="text-xs">{coin.signal_direction}</div>
            </div>
            <div className="mt-1 text-xs text-[var(--nq-text-secondary)]">{coin.name}</div>
            <div className="mt-2 flex items-center justify-between text-xs">
              <span>{Number(livePrice).toLocaleString("en-IN", { maximumFractionDigits: 2 })}</span>
              <span>{Number(liveChange) >= 0 ? "+" : ""}{safeFormat(liveChange, 2)}%</span>
            </div>
          </Link>
          );
        })}
        {loading
          ? Array.from({ length: 4 }, (_, i) => (
              <div key={`crypto-skeleton-${i}`} className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3 text-sm">
                <div className="h-3 w-24 rounded bg-[rgba(255,255,255,0.10)]" />
                <div className="mt-2 h-3 w-32 rounded bg-[rgba(255,255,255,0.08)]" />
                <div className="mt-2 h-3 w-20 rounded bg-[rgba(255,255,255,0.10)]" />
              </div>
            ))
          : null}
      </div>
    </main>
  );
}
