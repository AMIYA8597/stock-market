"use client";

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
  return (
    <aside className="max-h-[30vh] overflow-hidden border-b border-[var(--nq-border)] bg-[var(--nq-bg-secondary)] p-2 sm:p-3 lg:max-h-none lg:border-b-0 lg:border-r">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-[10px] uppercase tracking-[0.12em] text-[var(--nq-text-secondary)] sm:text-xs">Watchlist</h2>
        <span className="text-[10px] text-[var(--nq-text-secondary)] sm:text-xs">{signals.length} assets</span>
      </div>

      <div className="mb-1.5 flex gap-1.5 overflow-x-auto pb-1 lg:hidden">
        {signals.map((item) => {
          const selected = item.symbol === selectedSymbol;
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
                <span className="font-mono text-[10px] text-[var(--nq-text-primary)] sm:text-xs">{item.symbol}</span>
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
        {signals.map((item) => {
          const selected = item.symbol === selectedSymbol;
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
                <span className="font-mono text-xs text-[var(--nq-text-primary)]">{item.symbol}</span>
                <span className={`text-xs font-medium ${directionColor(item.ensemble.direction)}`}>
                  {item.ensemble.direction}
                </span>
              </div>
              <div className="mt-1 text-[11px] text-[var(--nq-text-secondary)]">
                Confidence {(item.ensemble.confidence * 100).toFixed(1)}%
              </div>
              <div className="mt-0.5 text-[10px] text-[var(--nq-text-secondary)]">
                {new Date(item.timestamp).toLocaleTimeString()}
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
}
