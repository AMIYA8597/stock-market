/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
"use client";

import { useState, useEffect } from "react";
import { screenerApi } from "@/lib/api-client";
import { safeFormat } from "@/lib/formatters";

interface ScannersTabProps {
  onSelectSymbol?: (symbol: string) => void;
}

export default function ScannersTab({
  onSelectSymbol,
}: ScannersTabProps): JSX.Element {
  const [scannerItems, setScannerItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const fetchScreener = async () => {
      try {
        setLoading(true);
        const res = await screenerApi.search({
          limit: 10,
          sort_by: "sharpe_21d"
        });
        if (mounted) {
          setScannerItems(res.results);
        }
      } catch (err) {
        console.error("Screener API error:", err);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    void fetchScreener();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="overflow-x-auto min-h-[150px]">
      <table className="w-full text-left text-[10px] font-mono">
        <thead>
          <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-muted)] uppercase tracking-wider text-[8px]">
            <th className="pb-1.5">Symbol</th>
            <th className="pb-1.5">Price</th>
            <th className="pb-1.5">1D Change</th>
            <th className="pb-1.5">RSI (14)</th>
            <th className="pb-1.5">ML Signal</th>
            <th className="pb-1.5 text-right">Action</th>
          </tr>
        </thead>
        <tbody>
          {loading ? (
            <tr>
              <td colSpan={6} className="py-6 text-center text-[var(--nq-text-muted)] italic">
                Scanning universe...
              </td>
            </tr>
          ) : scannerItems.length === 0 ? (
            <tr>
              <td colSpan={6} className="py-6 text-center text-[var(--nq-text-muted)] italic">
                No matching symbols found in current regime.
              </td>
            </tr>
          ) : (
            scannerItems.map((item) => {
              const rsi = item.rsi ?? 0;
              const chg = item.change_percent ?? 0;
              const signal = item.ml_signal?.toUpperCase() || "NEUTRAL";
              const isBullish = signal.includes("BULL") || signal === "BUY";
              const isBearish = signal.includes("BEAR") || signal === "SELL";

              return (
                <tr
                  key={item.symbol}
                  className="border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.06)] transition-colors glass-panel glow-hover fade-in"
                >
                  <td className="py-1.5 font-bold text-[var(--nq-text-primary)]">
                    {item.symbol}
                  </td>
                  <td className="py-1.5 text-[var(--nq-text-secondary)]">
                    {safeFormat(item.price, 2)}
                  </td>
                  <td
                    className={`py-1.5 ${chg >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}
                  >
                    {chg >= 0 ? "+" : ""}
                    {safeFormat(chg, 2)}%
                  </td>
                  <td className="py-1.5 text-[var(--nq-text-secondary)]">
                    {safeFormat(rsi, 1)}
                  </td>
                  <td className="py-1.5">
                    <span
                      className={`inline-flex rounded px-1.5 py-0.5 text-[8px] font-semibold border ${
                        isBullish
                          ? "bg-[rgba(0,230,118,0.08)] border-[rgba(0,230,118,0.2)] text-[#00E676]"
                          : isBearish
                            ? "bg-[rgba(255,59,92,0.08)] border-[rgba(255,59,92,0.2)] text-[#FF3B5C]"
                            : "bg-[rgba(255,255,255,0.04)] border-[rgba(255,255,255,0.1)] text-[var(--nq-text-secondary)]"
                      }`}
                    >
                      {signal}
                    </span>
                  </td>
                  <td className="py-1.5 text-right">
                    <button
                      type="button"
                      onClick={() => onSelectSymbol?.(item.symbol)}
                      className="rounded border border-[var(--nq-border)] hover:border-[var(--nq-accent-cyan)] hover:text-[var(--nq-text-primary)] px-2 py-0.5 text-[9px] text-[var(--nq-text-secondary)] transition-colors"
                    >
                      Load
                    </button>
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
