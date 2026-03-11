"use client";

import { useState } from "react";
import { Search, Filter, Download, Star, BookmarkPlus } from "lucide-react";
import {
  Card, CardHeader, CardTitle, Button, Badge, Input, Sparkline,
  cn, formatPrice, formatPercent, formatCompact, getPriceColor, getDirectionArrow,
} from "@neuroquant/ui";

const PRESETS = [
  { label: "AI High Conviction Longs", desc: "Model conf>75%, bull regime, positive sentiment" },
  { label: "Mean Reversion Candidates", desc: "RSI<30, near support, positive sentiment" },
  { label: "Momentum Leaders", desc: "Above all MAs, high RVOL, strong fundamentals" },
  { label: "Value + Quality", desc: "Low P/E, high ROE, low debt, positive momentum" },
];

const SCREENER_RESULTS = [
  { symbol: "TATAMOTORS", name: "Tata Motors", sector: "Auto", price: 985.40, changePct: 3.52, volume: 28400000, marketCap: 330000000000, rsi: 62, signal: "BUY", confidence: 82, sparkData: [920, 935, 950, 960, 970, 980, 985] },
  { symbol: "ITC", name: "ITC Ltd", sector: "FMCG", price: 468.20, changePct: 2.14, volume: 18900000, marketCap: 584000000000, rsi: 58, signal: "BUY", confidence: 76, sparkData: [440, 445, 450, 455, 460, 465, 468] },
  { symbol: "SBIN", name: "State Bank of India", sector: "Banking", price: 648.30, changePct: 1.82, volume: 22100000, marketCap: 578000000000, rsi: 55, signal: "BUY", confidence: 74, sparkData: [620, 625, 630, 635, 640, 645, 648] },
  { symbol: "TATASTEEL", name: "Tata Steel", sector: "Metals", price: 158.90, changePct: 2.81, volume: 34500000, marketCap: 194000000000, rsi: 64, signal: "BUY", confidence: 71, sparkData: [148, 150, 152, 154, 156, 157, 158] },
  { symbol: "ONGC", name: "ONGC", sector: "Energy", price: 278.45, changePct: 1.62, volume: 15600000, marketCap: 350000000000, rsi: 52, signal: "HOLD", confidence: 65, sparkData: [268, 270, 272, 274, 276, 277, 278] },
];

export function ScreenerContent() {
  const [activePreset, setActivePreset] = useState(0);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl font-bold text-nq-text-primary">AI Stock Screener</h1>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm"><BookmarkPlus className="h-3.5 w-3.5" /> Save Screen</Button>
          <Button variant="secondary" size="sm"><Download className="h-3.5 w-3.5" /> Export CSV</Button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4">
        {/* Filter panel */}
        <div className="col-span-12 lg:col-span-3 space-y-4">
          <Card>
            <CardHeader><CardTitle>Presets</CardTitle></CardHeader>
            <div className="space-y-1.5">
              {PRESETS.map((p, i) => (
                <button
                  key={i}
                  onClick={() => setActivePreset(i)}
                  className={cn(
                    "w-full rounded-nq px-3 py-2 text-left transition-colors",
                    activePreset === i ? "bg-nq-accent/10 border border-nq-accent/20" : "hover:bg-nq-bg-elevated border border-transparent"
                  )}
                >
                  <div className="text-xs font-medium text-nq-text-primary">{p.label}</div>
                  <div className="text-[10px] text-nq-text-tertiary mt-0.5">{p.desc}</div>
                </button>
              ))}
            </div>
          </Card>

          <Card>
            <CardHeader><CardTitle>Filters</CardTitle></CardHeader>
            <div className="space-y-3">
              {[
                { label: "RSI Range", min: "0", max: "100" },
                { label: "P/E Range", min: "0", max: "100" },
                { label: "Market Cap (Cr)", min: "1000", max: "" },
              ].map((f) => (
                <div key={f.label}>
                  <label className="text-[10px] text-nq-text-tertiary mb-1 block">{f.label}</label>
                  <div className="flex gap-2">
                    <Input placeholder="Min" defaultValue={f.min} className="h-7 text-[11px]" />
                    <Input placeholder="Max" defaultValue={f.max} className="h-7 text-[11px]" />
                  </div>
                </div>
              ))}
              <div className="flex items-center gap-2">
                <input type="checkbox" defaultChecked className="rounded border-nq-border bg-nq-bg-secondary" />
                <span className="text-xs text-nq-text-secondary">Above SMA 200</span>
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" className="rounded border-nq-border bg-nq-bg-secondary" />
                <span className="text-xs text-nq-text-secondary">Volume Surge (&gt;2x avg)</span>
              </div>
              <div>
                <label className="text-[10px] text-nq-text-tertiary mb-1 block">AI Confidence Min</label>
                <Input type="number" placeholder="70" defaultValue="70" className="h-7 text-[11px]" />
              </div>
              <Button className="w-full" size="sm"><Search className="h-3.5 w-3.5" /> Run Screener</Button>
            </div>
          </Card>
        </div>

        {/* Results table */}
        <div className="col-span-12 lg:col-span-9">
          <Card noPadding>
            <CardHeader className="px-4 pt-3">
              <CardTitle>{SCREENER_RESULTS.length} stocks found</CardTitle>
              <Badge variant="accent">Live</Badge>
            </CardHeader>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-nq-border bg-nq-bg-elevated/50">
                    {["Symbol", "Price", "Chg%", "Volume", "Mkt Cap", "RSI", "AI Signal", "Conf", ""].map((h) => (
                      <th key={h} className="px-3 py-2 text-left text-[10px] font-medium text-nq-text-tertiary uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-nq-border">
                  {SCREENER_RESULTS.map((r) => (
                    <tr key={r.symbol} className="hover:bg-nq-bg-card/50 transition-colors cursor-pointer">
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <div>
                            <div className="font-mono font-semibold text-nq-text-primary">{r.symbol}</div>
                            <div className="text-[10px] text-nq-text-tertiary">{r.sector}</div>
                          </div>
                          <Sparkline data={r.sparkData} width={40} height={14} />
                        </div>
                      </td>
                      <td className="px-3 py-2.5 font-mono font-semibold text-nq-text-primary">{formatPrice(r.price)}</td>
                      <td className={cn("px-3 py-2.5 font-mono font-medium", getPriceColor(r.changePct))}>
                        {getDirectionArrow(r.changePct)} {formatPercent(r.changePct)}
                      </td>
                      <td className="px-3 py-2.5 font-mono text-nq-text-secondary">{formatCompact(r.volume)}</td>
                      <td className="px-3 py-2.5 font-mono text-nq-text-secondary">{formatCompact(r.marketCap)}</td>
                      <td className="px-3 py-2.5 font-mono text-nq-text-secondary">{r.rsi}</td>
                      <td className="px-3 py-2.5">
                        <Badge variant={r.signal === "BUY" ? "bull" : r.signal === "SELL" ? "bear" : "default"}>{r.signal}</Badge>
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-1">
                          <div className="w-12 h-1.5 rounded-full bg-nq-bg-elevated overflow-hidden">
                            <div className="h-full rounded-full bg-nq-accent" style={{ width: `${r.confidence}%` }} />
                          </div>
                          <span className="font-mono text-[10px] text-nq-text-tertiary">{r.confidence}%</span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5">
                        <Button variant="ghost" size="sm" className="h-6 text-[10px]"><Star className="h-3 w-3" /></Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
