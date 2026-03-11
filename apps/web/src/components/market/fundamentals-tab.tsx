"use client";

import { CardTitle, cn, formatCompact } from "@neuroquant/ui";

interface FundamentalsTabProps {
  symbol: string;
}

const KEY_RATIOS = [
  { label: "P/E Ratio", value: "28.4", sector: "24.1", change: "above" },
  { label: "P/B Ratio", value: "3.2", sector: "2.8", change: "above" },
  { label: "EV/EBITDA", value: "16.8", sector: "14.2", change: "above" },
  { label: "ROE", value: "12.8%", sector: "15.2%", change: "below" },
  { label: "Debt/Equity", value: "0.42", sector: "0.65", change: "below" },
  { label: "Dividend Yield", value: "0.32%", sector: "1.1%", change: "below" },
  { label: "Revenue Growth", value: "18.4%", sector: "12.3%", change: "above" },
  { label: "Net Margin", value: "11.2%", sector: "9.8%", change: "above" },
];

const INCOME_DATA = [
  { year: "FY22", revenue: 792394, profit: 67845 },
  { year: "FY23", revenue: 942159, profit: 73670 },
  { year: "FY24", revenue: 1012458, profit: 79432 },
  { year: "FY25E", revenue: 1125000, profit: 88500 },
];

export function FundamentalsTab({ symbol }: FundamentalsTabProps) {
  const maxRevenue = Math.max(...INCOME_DATA.map((d) => d.revenue));

  return (
    <div className="space-y-4">
      {/* Key Ratios */}
      <div>
        <CardTitle className="mb-2">Key Ratios</CardTitle>
        <div className="space-y-1.5">
          {KEY_RATIOS.map((r) => (
            <div key={r.label} className="flex items-center justify-between py-0.5">
              <span className="text-xs text-nq-text-secondary">{r.label}</span>
              <div className="flex items-center gap-3">
                <span className="font-mono text-xs font-semibold text-nq-text-primary">{r.value}</span>
                <span className="text-[10px] text-nq-text-tertiary">vs {r.sector}</span>
                <div className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  r.change === "above" ? "bg-nq-bull" : "bg-nq-bear"
                )} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Revenue Trend */}
      <div>
        <CardTitle className="mb-2">Revenue Trend (₹ Cr)</CardTitle>
        <div className="space-y-1.5">
          {INCOME_DATA.map((d) => (
            <div key={d.year} className="flex items-center gap-3">
              <span className="w-12 font-mono text-[10px] text-nq-text-tertiary">{d.year}</span>
              <div className="flex-1 h-3 rounded-full bg-nq-bg-elevated overflow-hidden">
                <div
                  className="h-full rounded-full bg-nq-accent/60"
                  style={{ width: `${(d.revenue / maxRevenue) * 100}%` }}
                />
              </div>
              <span className="w-14 text-right font-mono text-[10px] text-nq-text-secondary">
                {formatCompact(d.revenue * 10000000)}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* DCF Valuation */}
      <div className="rounded-nq bg-nq-bg-elevated p-3">
        <CardTitle className="mb-2">DCF Fair Value</CardTitle>
        <div className="flex items-center justify-between">
          <div>
            <span className="font-mono text-lg font-bold text-nq-bull">₹3,102</span>
            <div className="text-[10px] text-nq-text-tertiary">8.9% upside</div>
          </div>
          <div className="text-right">
            <div className="text-[10px] text-nq-text-tertiary">Margin of Safety</div>
            <span className="font-mono text-sm font-semibold text-nq-warning">8.2%</span>
          </div>
        </div>
      </div>
    </div>
  );
}
