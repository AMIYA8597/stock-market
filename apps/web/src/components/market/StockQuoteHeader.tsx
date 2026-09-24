/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
"use client";

import React from "react";
import { Quote } from "@neuroquant/types";
import { safeFormat } from "@/lib/formatters";
import { Clock, AlertTriangle, TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@neuroquant/ui";

interface StockQuoteHeaderProps {
  symbol: string;
  quote: Quote | null;
  livePrice?: number;
  liveChange?: number;
}

export function StockQuoteHeader({ symbol, quote, livePrice, liveChange }: StockQuoteHeaderProps) {
  if (!quote) return null;

  const currentPrice = livePrice ?? quote.price;
  const currentChange = liveChange ?? quote.change_percent;
  const isPositive = currentChange >= 0;

  // Compute day range position (0 to 100%)
  let rangePercent = 0;
  if (quote.high && quote.low) {
    const range = quote.high - quote.low;
    if (range > 0) {
      rangePercent = ((currentPrice - quote.low) / range) * 100;
      rangePercent = Math.max(0, Math.min(100, rangePercent));
    }
  }

  // Determine market status / provenance
  const isDelayed = true; // By default backend says delayed ~15 min
  const isClosed = false; // Could derive from a market status API

  return (
    <div className="flex flex-col gap-4 border-b border-nq-border pb-6">
      {/* Top Row: Symbol, Price, Change */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-nq-text-primary uppercase tracking-tight flex items-center gap-3">
            {symbol}
            <span
              className={cn(
                "flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded border uppercase tracking-wider",
                (quote.source === "realtime")
                  ? "text-[#00E676] border-[#00E676] bg-[rgba(0,230,118,0.1)]"
                  : (quote.source === "computed")
                    ? "text-[#B388FF] border-[#B388FF] bg-[rgba(179,136,255,0.1)]"
                    : "text-[#FFB800] border-[#FFB800] bg-[rgba(255,184,0,0.1)]"
              )}
            >
              {quote.source === "realtime" ? "Real-time" : quote.source === "computed" ? "Computed" : "Delayed"}
            </span>
            {isClosed && (
              <span className="flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded bg-[var(--nq-bg-elevated)] border border-[var(--nq-border)] text-nq-text-tertiary uppercase tracking-wider">
                Market Closed
              </span>
            )}
          </h1>
        </div>

        <div className="flex flex-col items-start md:items-end">
          <div className="flex items-baseline gap-3">
            <span className="text-3xl font-mono font-bold text-nq-text-primary">
              ₹{Number(currentPrice).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <span
              className={cn(
                "flex items-center text-lg font-mono font-semibold",
                isPositive ? "text-[#00E676]" : "text-[#FF3B5C]"
              )}
            >
              {isPositive ? <TrendingUp className="w-5 h-5 mr-1" /> : <TrendingDown className="w-5 h-5 mr-1" />}
              {isPositive ? "+" : ""}
              {safeFormat(currentChange, 2)}%
            </span>
          </div>
          <div className="text-xs text-nq-text-tertiary font-mono mt-1 flex gap-3">
            <span>O: {safeFormat(quote.open, 2)}</span>
            <span>H: {safeFormat(quote.high, 2)}</span>
            <span>L: {safeFormat(quote.low, 2)}</span>
            <span>C: {safeFormat(quote.previous_close, 2)}</span>
          </div>
        </div>
      </div>

      {/* Day Range Bar */}
      {quote.low && quote.high && (
        <div className="mt-2 p-3 bg-nq-bg-card border border-nq-border rounded-lg max-w-md w-full">
          <div className="flex justify-between text-xs text-nq-text-tertiary font-mono mb-2">
            <span>Day L: ₹{safeFormat(quote.low, 1)}</span>
            <span>Day H: ₹{safeFormat(quote.high, 1)}</span>
          </div>
          <div className="relative h-2 w-full bg-nq-bg-elevated rounded-full overflow-hidden">
            <div
              className="absolute top-0 bottom-0 left-0 bg-gradient-to-r from-nq-bg-elevated via-nq-text-secondary to-nq-accent opacity-50"
              style={{ width: `${rangePercent}%` }}
            />
            {/* Current price marker */}
            <div
              className="absolute top-0 bottom-0 w-1 bg-nq-accent shadow-[0_0_8px_var(--nq-accent)]"
              style={{ left: `calc(${rangePercent}% - 2px)` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
