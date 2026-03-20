"use client";

import { ArrowDown, ArrowUp, Sparkles, TrendingUp } from "lucide-react";
import { useEffect, useState } from "react";

interface Stock {
  ticker: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  signal_direction: "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL";
  confidence: number;
}

const signalColor = (direction: string): string => {
  if (direction.includes("BUY")) return "text-[#00E676]";
  if (direction.includes("SELL")) return "text-[#FF3B5C]";
  return "text-[#FFB800]";
};

const signalBg = (direction: string): string => {
  if (direction.includes("BUY")) return "bg-[rgba(0,230,118,0.12)]";
  if (direction.includes("SELL")) return "bg-[rgba(255,59,92,0.12)]";
  return "bg-[rgba(255,184,0,0.08)]";
};

export default function StockTable({ stocks }: { stocks: Stock[] }): JSX.Element {
  const [filtered, setFiltered] = useState<Stock[]>(stocks);
  const [sortBy, setSortBy] = useState<"price" | "change" | "confidence">("price");

  useEffect(() => {
    const sorted = [...stocks].sort((a, b) => {
      if (sortBy === "price") return b.price - a.price;
      if (sortBy === "change") return b.change_pct - a.change_pct;
      return b.confidence - a.confidence;
    });
    setFiltered(sorted);
  }, [stocks, sortBy]);

  return (
    <div className="w-full space-y-4">
      {/* Header Controls */}
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-[var(--nq-text-primary)] flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-[#00D4F5] animate-pulse" />
          Stock Universe
        </h2>
        <div className="flex gap-2">
          {(["price", "change", "confidence"] as const).map((sort) => (
            <button
              key={sort}
              onClick={() => setSortBy(sort)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition ${
                sortBy === sort
                  ? "bg-[#00D4F5] text-[#07090F]"
                  : "bg-[var(--nq-bg-elevated)] text-[var(--nq-text-secondary)] hover:bg-[var(--nq-bg-overlay)]"
              }`}
            >
              {sort.charAt(0).toUpperCase() + sort.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto scrollbar-thin">
        <table className="w-full border-collapse text-sm">
          <thead className="sticky top-0 bg-[var(--nq-bg-elevated)] border-b border-[var(--nq-border)]">
            <tr>
              <th className="px-4 py-2 text-left font-semibold text-[var(--nq-text-secondary)]">Ticker</th>
              <th className="px-4 py-2 text-right font-semibold text-[var(--nq-text-secondary)]">Price</th>
              <th className="px-4 py-2 text-right font-semibold text-[var(--nq-text-secondary)]">Change</th>
              <th className="px-4 py-2 text-center font-semibold text-[var(--nq-text-secondary)]">Signal</th>
              <th className="px-4 py-2 text-right font-semibold text-[var(--nq-text-secondary)]">Confidence</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--nq-border)]">
            {filtered.map((stock) => (
              <tr
                key={stock.ticker}
                className="hover:bg-[var(--nq-bg-elevated)] transition-colors cursor-pointer group"
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <TrendingUp className={`h-4 w-4 ${stock.change_pct >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"} group-hover:animate-spin`} />
                    <div>
                      <div className="font-mono font-semibold text-[var(--nq-text-primary)]">{stock.ticker}</div>
                      <div className="text-xs text-[var(--nq-text-secondary)]">{stock.name}</div>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 text-right font-mono text-[var(--nq-text-primary)]">₹{stock.price.toFixed(2)}</td>
                <td className="px-4 py-3 text-right">
                  <div className={`flex items-center justify-end gap-1 font-mono font-semibold ${stock.change_pct >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
                    {stock.change_pct >= 0 ? <ArrowUp className="h-4 w-4" /> : <ArrowDown className="h-4 w-4" />}
                    {stock.change_pct.toFixed(2)}%
                  </div>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${signalBg(stock.signal_direction)} ${signalColor(stock.signal_direction)}`}>
                    {stock.signal_direction.split("_").join(" ")}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <div className="h-1.5 w-16 bg-[var(--nq-bg-elevated)] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#00D4F5] transition-all"
                        style={{ width: `${stock.confidence * 100}%` }}
                      />
                    </div>
                    <span className="text-[var(--nq-text-secondary)] text-xs w-10 text-right">{(stock.confidence * 100).toFixed(0)}%</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Info Footer */}
      <div className="rounded border border-[var(--nq-border)] bg-[rgba(0,212,255,0.05)] px-4 py-3 text-xs text-[var(--nq-text-secondary)]">
        <p>💡 Hover over rows to see details. Click to view full analysis. Signals update every minute with ensemble predictions.</p>
      </div>
    </div>
  );
}
