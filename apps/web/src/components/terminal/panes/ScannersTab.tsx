"use client";

import { useMemo } from "react";
import { safeFormat } from "@/lib/formatters";

interface ScannersTabProps {
  onSelectSymbol?: (symbol: string) => void;
}

export default function ScannersTab({ onSelectSymbol }: ScannersTabProps): JSX.Element {
  const scannerItems = useMemo(
    () => [
      { symbol: "RELIANCE", price: 2452.15, chg: 1.45, rsi: 58.2, condition: "EMA 9/21 Crossover", type: "bullish" },
      { symbol: "TCS", price: 3820.40, chg: -0.85, rsi: 35.4, condition: "RSI Oversold", type: "bullish" },
      { symbol: "INFY", price: 1425.60, chg: -1.90, rsi: 28.1, condition: "Hammer Detected", type: "bullish" },
      { symbol: "HDFCBANK", price: 1540.35, chg: 0.22, rsi: 50.5, condition: "Doji Reversal", type: "neutral" },
      { symbol: "ICICIBANK", price: 985.20, chg: 2.10, rsi: 74.8, condition: "RSI Overbought", type: "bearish" },
      { symbol: "SBIN", price: 742.60, chg: 3.45, rsi: 68.9, condition: "Engulfing Bullish", type: "bullish" },
      { symbol: "BHARTIENTL", price: 1120.50, chg: -2.30, rsi: 30.5, condition: "Shooting Star", type: "bearish" },
    ],
    []
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-[10px] font-mono">
        <thead>
          <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-muted)] uppercase tracking-wider text-[8px]">
            <th className="pb-1.5">Symbol</th>
            <th className="pb-1.5">Price</th>
            <th className="pb-1.5">1D Change</th>
            <th className="pb-1.5">RSI (14)</th>
            <th className="pb-1.5">Condition</th>
            <th className="pb-1.5 text-right">Action</th>
          </tr>
        </thead>
        <tbody>
          {scannerItems.map((item) => (
            <tr
              key={item.symbol}
              className="border-b border-[rgba(255,255,255,0.04)] hover:bg-[rgba(255,255,255,0.02)] transition-colors"
            >
              <td className="py-1.5 font-bold text-[var(--nq-text-primary)]">{item.symbol}</td>
              <td className="py-1.5 text-[var(--nq-text-secondary)]">{safeFormat(item.price, 2)}</td>
              <td className={`py-1.5 ${item.chg >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
                {item.chg >= 0 ? "+" : ""}
                {safeFormat(item.chg, 2)}%
              </td>
              <td className="py-1.5 text-[var(--nq-text-secondary)]">{safeFormat(item.rsi, 1)}</td>
              <td className="py-1.5">
                <span
                  className={`inline-flex rounded px-1.5 py-0.5 text-[8px] font-semibold border ${
                    item.type === "bullish"
                      ? "bg-[rgba(0,230,118,0.08)] border-[rgba(0,230,118,0.2)] text-[#00E676]"
                      : item.type === "bearish"
                      ? "bg-[rgba(255,59,92,0.08)] border-[rgba(255,59,92,0.2)] text-[#FF3B5C]"
                      : "bg-[rgba(255,255,255,0.04)] border-[rgba(255,255,255,0.1)] text-[var(--nq-text-secondary)]"
                  }`}
                >
                  {item.condition}
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
          ))}
        </tbody>
      </table>
    </div>
  );
}
