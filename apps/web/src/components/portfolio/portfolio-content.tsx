"use client";

import { Plus, Download, RefreshCw } from "lucide-react";
import {
  Card, CardHeader, CardTitle, Button, Badge, PriceDisplay, Sparkline,
  cn, formatPrice, formatPercent, getPriceColor, getDirectionArrow,
} from "@neuroquant/ui";

interface HoldingRow {
  symbol: string; name: string; qty: number; avgCost: number; ltp: number;
  pnl: number; pnlPct: number; dayChg: number; weight: number; varContrib: number;
  signal: string; sparkData: number[];
}

const HOLDINGS: HoldingRow[] = [
  { symbol: "RELIANCE", name: "Reliance Industries", qty: 50, avgCost: 2720, ltp: 2847.65, pnl: 6382.5, pnlPct: 4.69, dayChg: 1.24, weight: 22.1, varContrib: 3.2, signal: "BUY", sparkData: [2720, 2740, 2760, 2780, 2800, 2820, 2847] },
  { symbol: "TCS", name: "TCS", qty: 30, avgCost: 3890, ltp: 3842.30, pnl: -1431, pnlPct: -1.23, dayChg: -0.82, weight: 17.9, varContrib: 2.8, signal: "HOLD", sparkData: [3890, 3880, 3870, 3860, 3850, 3845, 3842] },
  { symbol: "HDFCBANK", name: "HDFC Bank", qty: 80, avgCost: 1580, ltp: 1645.20, pnl: 5216, pnlPct: 4.13, dayChg: 0.52, weight: 20.4, varContrib: 2.1, signal: "BUY", sparkData: [1580, 1600, 1610, 1620, 1630, 1640, 1645] },
  { symbol: "INFY", name: "Infosys", qty: 60, avgCost: 1520, ltp: 1478.90, pnl: -2466, pnlPct: -2.70, dayChg: -1.52, weight: 13.8, varContrib: 4.1, signal: "SELL", sparkData: [1520, 1510, 1500, 1490, 1485, 1480, 1478] },
  { symbol: "ICICIBANK", name: "ICICI Bank", qty: 100, avgCost: 1020, ltp: 1068.45, pnl: 4845, pnlPct: 4.75, dayChg: 0.91, weight: 16.6, varContrib: 1.9, signal: "BUY", sparkData: [1020, 1030, 1040, 1050, 1060, 1065, 1068] },
  { symbol: "SBIN", name: "State Bank of India", qty: 120, avgCost: 620, ltp: 648.30, pnl: 3396, pnlPct: 4.56, dayChg: 1.82, weight: 12.1, varContrib: 2.4, signal: "HOLD", sparkData: [620, 625, 630, 635, 640, 645, 648] },
];

const OPTIMIZATION_METHODS = [
  { value: "max_sharpe", label: "Max Sharpe" },
  { value: "min_vol", label: "Min Variance" },
  { value: "hrp", label: "HRP" },
  { value: "equal", label: "Equal Weight" },
];

export function PortfolioContent() {
  const totalValue = HOLDINGS.reduce((s, h) => s + h.ltp * h.qty, 0);
  const totalPnl = HOLDINGS.reduce((s, h) => s + h.pnl, 0);
  const totalPnlPct = (totalPnl / (totalValue - totalPnl)) * 100;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl font-bold text-nq-text-primary">Portfolio Manager</h1>
          <div className="mt-1 flex items-center gap-3">
            <PriceDisplay price={totalValue} changePercent={totalPnlPct} size="md" />
            <Badge variant={totalPnl >= 0 ? "bull" : "bear"}>
              {totalPnl >= 0 ? "+" : ""}{formatPrice(totalPnl)} today
            </Badge>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm"><Download className="h-3.5 w-3.5" /> Export</Button>
          <Button size="sm"><Plus className="h-3.5 w-3.5" /> Add Holding</Button>
        </div>
      </div>

      {/* Holdings Table */}
      <Card noPadding>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-nq-border bg-nq-bg-elevated/50">
                {["Symbol", "Qty", "Avg Cost", "LTP", "P&L", "P&L%", "Day Chg", "Weight", "VaR", "Signal", ""].map((h) => (
                  <th key={h} className="px-3 py-2.5 text-left text-[10px] font-medium text-nq-text-tertiary uppercase tracking-wider whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-nq-border">
              {HOLDINGS.map((h) => (
                <tr key={h.symbol} className="hover:bg-nq-bg-card/50 transition-colors">
                  <td className="px-3 py-2.5">
                    <div className="flex items-center gap-2">
                      <div>
                        <div className="font-mono font-semibold text-nq-text-primary">{h.symbol}</div>
                        <div className="text-[10px] text-nq-text-tertiary">{h.name}</div>
                      </div>
                      <Sparkline data={h.sparkData} width={48} height={16} />
                    </div>
                  </td>
                  <td className="px-3 py-2.5 font-mono text-nq-text-primary">{h.qty}</td>
                  <td className="px-3 py-2.5 font-mono text-nq-text-secondary">{formatPrice(h.avgCost)}</td>
                  <td className="px-3 py-2.5 font-mono font-semibold text-nq-text-primary">{formatPrice(h.ltp)}</td>
                  <td className={cn("px-3 py-2.5 font-mono font-medium", getPriceColor(h.pnl))}>
                    {h.pnl >= 0 ? "+" : ""}{formatPrice(h.pnl)}
                  </td>
                  <td className={cn("px-3 py-2.5 font-mono font-medium", getPriceColor(h.pnlPct))}>
                    {getDirectionArrow(h.pnlPct)} {formatPercent(h.pnlPct)}
                  </td>
                  <td className={cn("px-3 py-2.5 font-mono", getPriceColor(h.dayChg))}>
                    {formatPercent(h.dayChg)}
                  </td>
                  <td className="px-3 py-2.5 font-mono text-nq-text-secondary">{h.weight.toFixed(1)}%</td>
                  <td className="px-3 py-2.5 font-mono text-nq-text-secondary">{h.varContrib.toFixed(1)}%</td>
                  <td className="px-3 py-2.5">
                    <Badge variant={h.signal === "BUY" ? "bull" : h.signal === "SELL" ? "bear" : "default"}>
                      {h.signal}
                    </Badge>
                  </td>
                  <td className="px-3 py-2.5">
                    <Button variant="ghost" size="sm" className="h-6 text-[10px]">View</Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Analytics grid */}
      <div className="grid grid-cols-12 gap-4">
        {/* Allocation donuts */}
        <Card className="col-span-12 lg:col-span-4">
          <CardHeader><CardTitle>Sector Allocation</CardTitle></CardHeader>
          <div className="flex items-center justify-center py-4">
            <div className="space-y-2 w-full">
              {[
                { sector: "Banking", weight: 49.1, color: "#00D4FF" },
                { sector: "IT", weight: 31.7, color: "#FF3B3B" },
                { sector: "Energy", weight: 22.1, color: "#00E676" },
              ].map((s) => (
                <div key={s.sector} className="flex items-center gap-2">
                  <div className="h-2 w-2 rounded-full" style={{ backgroundColor: s.color }} />
                  <span className="text-xs text-nq-text-secondary flex-1">{s.sector}</span>
                  <div className="w-24 h-1.5 rounded-full bg-nq-bg-elevated overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${s.weight}%`, backgroundColor: s.color }} />
                  </div>
                  <span className="font-mono text-[10px] text-nq-text-tertiary w-10 text-right">{s.weight}%</span>
                </div>
              ))}
            </div>
          </div>
        </Card>

        {/* Risk summary */}
        <Card className="col-span-12 lg:col-span-4">
          <CardHeader><CardTitle>Risk Metrics</CardTitle></CardHeader>
          <div className="space-y-2">
            {[
              { label: "VaR (95%)", value: "₹18,420", color: "text-nq-warning" },
              { label: "CVaR (95%)", value: "₹24,180", color: "text-nq-bear" },
              { label: "Max Drawdown", value: "-8.4%", color: "text-nq-bear" },
              { label: "Sharpe (90d)", value: "1.42", color: "text-nq-bull" },
              { label: "Beta", value: "0.87", color: "text-nq-text-primary" },
            ].map((m) => (
              <div key={m.label} className="flex items-center justify-between">
                <span className="text-xs text-nq-text-secondary">{m.label}</span>
                <span className={cn("font-mono text-xs font-semibold", m.color)}>{m.value}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Rebalancing */}
        <Card className="col-span-12 lg:col-span-4">
          <CardHeader>
            <CardTitle>Rebalance</CardTitle>
            <Button variant="secondary" size="sm"><RefreshCw className="h-3 w-3" /> Optimize</Button>
          </CardHeader>
          <div className="space-y-2">
            <div className="flex gap-1 flex-wrap">
              {OPTIMIZATION_METHODS.map((m) => (
                <Button key={m.value} variant="ghost" size="sm" className="text-[10px] h-6 px-2">{m.label}</Button>
              ))}
            </div>
            <div className="text-xs text-nq-text-secondary space-y-1 mt-2">
              <p>Current portfolio Sharpe: <span className="font-mono font-semibold text-nq-text-primary">1.42</span></p>
              <p>Optimal Sharpe: <span className="font-mono font-semibold text-nq-bull">1.78</span></p>
              <p>Est. rebalance cost: <span className="font-mono text-nq-warning">₹1,240</span></p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
