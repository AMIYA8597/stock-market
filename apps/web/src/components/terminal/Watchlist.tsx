"use client";

import { useMemo, useState } from "react";
import type { SignalResponse } from "@/types/intelligence";

interface WatchlistProps {
  signals: SignalResponse[];
  selectedSymbol: string;
  onSelectSymbol: (symbol: string) => void;
}

const directionColor = (direction: string): string => {
  if (direction.includes("BUY")) return "text-[#00E676]";
  if (direction.includes("SELL")) return "text-[#FF3B5C]";
  return "text-[#FFB800]";
};

export default function Watchlist({ signals, selectedSymbol, onSelectSymbol }: WatchlistProps): JSX.Element {
  const [tab, setTab] = useState<"watchlist" | "market">("watchlist");

  const visibleSignals = useMemo(() => {
    if (tab === "watchlist") {
      return signals.slice(0, 8);
    }
    return [...signals].sort((a, b) => b.ensemble.confidence - a.ensemble.confidence);
  }, [signals, tab]);

  return (
    <aside className="h-full overflow-hidden border-b border-[var(--nq-border)] bg-[var(--nq-bg-secondary)] p-2 sm:p-3 lg:max-h-none lg:border-b-0 lg:border-r">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-[10px] uppercase tracking-[0.12em] text-[var(--nq-text-secondary)] sm:text-xs">Watchlist</h2>
        <span className="text-[10px] text-[var(--nq-text-secondary)] sm:text-xs">{signals.length} assets</span>
      </div>

      <div className="mb-2 grid grid-cols-2 gap-1 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] p-1">
        <button
          type="button"
          onClick={() => setTab("watchlist")}
          className={`rounded px-2 py-1 text-[10px] uppercase tracking-[0.09em] ${tab === "watchlist" ? "bg-[var(--nq-bg-elevated)] text-[var(--nq-text-primary)]" : "text-[var(--nq-text-secondary)]"}`}
        >
          My Watchlist
        </button>
        <button
          type="button"
          onClick={() => setTab("market")}
          className={`rounded px-2 py-1 text-[10px] uppercase tracking-[0.09em] ${tab === "market" ? "bg-[var(--nq-bg-elevated)] text-[var(--nq-text-primary)]" : "text-[var(--nq-text-secondary)]"}`}
        >
          Market
        </button>
      </div>

      <div className="mb-1.5 flex gap-1.5 overflow-x-auto pb-1 lg:hidden">
        {/* Mobile-only quick watchlist strip */}
        {visibleSignals.map((item) => {
          const selected = item.symbol === selectedSymbol;
          const regimeDotColor =
            item.regime.state === "BULL"
              ? "bg-[var(--nq-accent-green)]"
              : item.regime.state === "BEAR"
                ? "bg-[var(--nq-accent-red)]"
                : item.regime.state === "CRISIS"
                  ? "bg-[var(--nq-accent-red)]"
                  : "bg-[var(--nq-accent-amber)]";
          return (
            <button
              key={item.symbol}
              type="button"
              className={`min-w-[132px] rounded border px-2 py-1.5 text-left transition sm:min-w-[150px] ${
                selected
                  ? "border-[var(--nq-accent)] bg-[var(--nq-bg-elevated)]"
                  : "border-[var(--nq-border)] bg-[var(--nq-bg-card)] hover:border-[var(--nq-border-hover)]"
              }`}
              onClick={() => onSelectSymbol(item.symbol)}
            >
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 font-mono text-[10px] text-[var(--nq-text-primary)] sm:text-xs">
                  <span className={`h-2 w-2 rounded-full ${regimeDotColor}`} />
                  {item.symbol}
                </span>
                <span className={`text-[10px] font-medium sm:text-xs ${directionColor(item.ensemble.direction)}`}>
                  {item.ensemble.direction}
                </span>
              </div>
              <div className="mt-1 text-[10px] text-[var(--nq-text-secondary)]">
                Confidence {(item.ensemble.confidence * 100).toFixed(1)}%
              </div>
              <div className="mt-0.5 text-[10px] text-[var(--nq-text-secondary)]">
                {new Date(item.timestamp).toLocaleTimeString()}
              </div>
            </button>
          );
        })}
      </div>

      <div className="hidden space-y-2 overflow-y-auto pr-1 lg:block">
        {visibleSignals.map((item) => {
          const selected = item.symbol === selectedSymbol;
          const regimeDotColor =
            item.regime.state === "BULL"
              ? "bg-[var(--nq-accent-green)]"
              : item.regime.state === "BEAR"
                ? "bg-[var(--nq-accent-red)]"
                : item.regime.state === "CRISIS"
                  ? "bg-[var(--nq-accent-red)]"
                  : "bg-[var(--nq-accent-amber)]";
          return (
            <button
              key={`desktop-${item.symbol}`}
              type="button"
              className={`w-full rounded border px-3 py-2 text-left transition ${
                selected
                  ? "border-[var(--nq-accent)] bg-[var(--nq-bg-elevated)]"
                  : "border-[var(--nq-border)] bg-[var(--nq-bg-card)] hover:border-[var(--nq-border-hover)]"
              }`}
              onClick={() => onSelectSymbol(item.symbol)}
            >
              <div className="flex items-center justify-between">
                <div className="min-w-0">
                  <span className="flex items-center gap-1.5 font-mono text-xs text-[var(--nq-text-primary)]">
                    <span className={`h-2 w-2 rounded-full ${regimeDotColor}`} />
                    {item.symbol}
                  </span>
                  <p className="mt-0.5 truncate text-[10px] text-[var(--nq-text-secondary)]">{item.symbol.replace(".NS", "")}</p>
                </div>
                <span className="text-right">
                  <span className={`block text-xs font-medium ${directionColor(item.ensemble.direction)}`}>{item.ensemble.direction}</span>
                  <span className="block text-[10px] text-[var(--nq-text-secondary)]">{(item.ensemble.confidence * 100).toFixed(1)}%</span>
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px] text-[var(--nq-text-secondary)]">
                <span>{item.regime.state}</span>
                <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
