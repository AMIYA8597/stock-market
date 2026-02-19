"use client";

import { useMemo } from "react";
import { cn, formatPrice, formatPercent, getPriceColor, getDirectionArrow, Sparkline } from "@neuroquant/ui";

interface TickerItem {
  symbol: string;
  label: string;
  price: number;
  change_pct: number;
  sparkData: number[];
  currency: string;
}

const TICKER_DATA: TickerItem[] = [
  { symbol: "NIFTY50", label: "Nifty 50", price: 22456.80, change_pct: 0.73, sparkData: [22200, 22250, 22180, 22320, 22400, 22380, 22456, 22490, 22520, 22456, 22470, 22430, 22456, 22480, 22510, 22456, 22420, 22450, 22480, 22456], currency: "₹" },
  { symbol: "SENSEX", label: "Sensex", price: 73852.94, change_pct: 0.68, sparkData: [73400, 73500, 73450, 73600, 73700, 73750, 73852, 73900, 73950, 73852, 73870, 73830, 73852, 73880, 73920, 73852, 73810, 73840, 73870, 73852], currency: "₹" },
  { symbol: "SPX", label: "S&P 500", price: 5234.18, change_pct: -0.32, sparkData: [5260, 5255, 5240, 5245, 5238, 5242, 5234, 5230, 5228, 5234, 5237, 5232, 5234, 5236, 5240, 5234, 5230, 5232, 5235, 5234], currency: "$" },
  { symbol: "IXIC", label: "NASDAQ", price: 16428.82, change_pct: -0.51, sparkData: [16500, 16490, 16460, 16470, 16450, 16445, 16428, 16420, 16415, 16428, 16435, 16425, 16428, 16430, 16440, 16428, 16420, 16425, 16430, 16428], currency: "$" },
  { symbol: "XAUUSD", label: "Gold", price: 2178.40, change_pct: 1.24, sparkData: [2150, 2155, 2160, 2158, 2165, 2170, 2178, 2180, 2185, 2178, 2175, 2172, 2178, 2182, 2186, 2178, 2176, 2174, 2179, 2178], currency: "$" },
  { symbol: "BTC-USD", label: "Bitcoin", price: 67842.50, change_pct: 2.18, sparkData: [66400, 66600, 66800, 67000, 67200, 67400, 67842, 68000, 68200, 67842, 67700, 67600, 67842, 67900, 68100, 67842, 67750, 67800, 67850, 67842], currency: "$" },
  { symbol: "USDINR", label: "USD/INR", price: 83.12, change_pct: -0.08, sparkData: [83.20, 83.18, 83.15, 83.16, 83.14, 83.13, 83.12, 83.11, 83.10, 83.12, 83.13, 83.12, 83.12, 83.11, 83.10, 83.12, 83.13, 83.12, 83.11, 83.12], currency: "₹" },
];

function TickerItemDisplay({ item }: { item: TickerItem }) {
  return (
    <div className="flex items-center gap-3 px-6 py-2 border-r border-nq-border/50 flex-shrink-0">
      <div className="flex flex-col">
        <span className="text-[10px] font-medium text-nq-text-tertiary uppercase tracking-wider">
          {item.label}
        </span>
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-semibold text-nq-text-primary">
            {formatPrice(item.price, item.currency)}
          </span>
          <span className={cn("flex items-center gap-0.5 text-xs font-medium font-mono", getPriceColor(item.change_pct))}>
            <span className="text-[9px]">{getDirectionArrow(item.change_pct)}</span>
            {formatPercent(item.change_pct)}
          </span>
        </div>
      </div>
      <Sparkline data={item.sparkData} width={60} height={20} positive={item.change_pct > 0} />
    </div>
  );
}

export function TickerStrip() {
  const items = useMemo(() => [...TICKER_DATA, ...TICKER_DATA], []);

  return (
    <div className="relative overflow-hidden rounded-nq-lg border border-nq-border bg-nq-bg-card">
      <div className="flex animate-ticker-scroll">
        {items.map((item, idx) => (
          <TickerItemDisplay key={`${item.symbol}-${idx}`} item={item} />
        ))}
      </div>
    </div>
  );
}
