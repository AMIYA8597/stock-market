"use client";

import { useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { ArrowLeft, Star, Share2, Download, ExternalLink } from "lucide-react";
import Link from "next/link";
import {
  Card, CardHeader, CardTitle, CardContent, Button, Badge, PriceDisplay,
  cn, formatCompact, formatVolume, RegimeBadge, LoadingState,
} from "@neuroquant/ui";
import type { Timeframe, ChartType } from "@neuroquant/types";
import { TradingChart } from "./trading-chart";
import { AiForecastTab } from "./ai-forecast-tab";
import { FundamentalsTab } from "./fundamentals-tab";

const TIMEFRAMES: Timeframe[] = ["1m", "5m", "15m", "1h", "4h", "1D", "1W", "1M"];

interface StockDetailContentProps {
  symbol: string;
}

export function StockDetailContent({ symbol }: StockDetailContentProps) {
  const [timeframe, setTimeframe] = useState<Timeframe>("1D");
  const [chartType, setChartType] = useState<ChartType>("candlestick");

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <Link href="/dashboard" className="text-nq-text-tertiary hover:text-nq-text-secondary">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-display text-xl font-bold text-nq-text-primary">{symbol}</h1>
              <Badge>NSE</Badge>
              <Badge variant="accent">INR</Badge>
            </div>
            <p className="text-sm text-nq-text-secondary">Reliance Industries Limited</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <PriceDisplay price={2847.65} changePercent={1.24} size="lg" />
          <div className="flex gap-1">
            <Button variant="ghost" size="icon"><Star className="h-4 w-4" /></Button>
            <Button variant="ghost" size="icon"><Share2 className="h-4 w-4" /></Button>
            <Button variant="ghost" size="icon"><Download className="h-4 w-4" /></Button>
          </div>
        </div>
      </div>

      {/* Key metrics badges */}
      <div className="flex flex-wrap gap-2">
        <Badge>Mkt Cap: {formatCompact(19200000000000)}</Badge>
        <Badge>P/E: 28.4</Badge>
        <Badge>Vol: {formatVolume(12450000)}</Badge>
        <Badge>VWAP: ₹2,841.20</Badge>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-nq-text-tertiary">52W</span>
          <div className="relative h-1.5 w-24 rounded-full bg-nq-bg-elevated">
            <div className="absolute left-0 top-0 h-full rounded-full bg-gradient-to-r from-nq-bear to-nq-bull" style={{ width: "72%" }} />
            <div className="absolute top-1/2 -translate-y-1/2 h-3 w-0.5 bg-nq-text-primary rounded" style={{ left: "72%" }} />
          </div>
          <span className="font-mono text-[10px] text-nq-text-tertiary">₹2,220 — ₹3,024</span>
        </div>
      </div>

      {/* Main content: Chart + Right Panel */}
      <div className="grid grid-cols-12 gap-4">
        {/* Chart area */}
        <div className="col-span-12 xl:col-span-8 space-y-3">
          {/* Timeframe + Chart type controls */}
          <Card noPadding>
            <div className="flex items-center justify-between px-3 py-2 border-b border-nq-border">
              <div className="flex gap-0.5">
                {TIMEFRAMES.map((tf) => (
                  <button
                    key={tf}
                    onClick={() => setTimeframe(tf)}
                    className={cn(
                      "rounded px-2 py-1 text-[11px] font-mono font-medium transition-colors",
                      timeframe === tf ? "bg-nq-accent/10 text-nq-accent" : "text-nq-text-tertiary hover:text-nq-text-secondary"
                    )}
                  >
                    {tf}
                  </button>
                ))}
              </div>
              <div className="flex gap-0.5">
                {(["candlestick", "line", "area"] as ChartType[]).map((ct) => (
                  <button
                    key={ct}
                    onClick={() => setChartType(ct)}
                    className={cn(
                      "rounded px-2 py-1 text-[11px] font-medium capitalize transition-colors",
                      chartType === ct ? "bg-nq-accent/10 text-nq-accent" : "text-nq-text-tertiary hover:text-nq-text-secondary"
                    )}
                  >
                    {ct}
                  </button>
                ))}
              </div>
            </div>
            <div className="h-[480px]">
              <TradingChart symbol={symbol} timeframe={timeframe} chartType={chartType} />
            </div>
          </Card>
        </div>

        {/* Right Panel — Tabs */}
        <div className="col-span-12 xl:col-span-4">
          <Card noPadding className="h-full">
            <Tabs.Root defaultValue="forecast" className="flex flex-col h-full">
              <Tabs.List className="flex border-b border-nq-border px-1">
                {[
                  { value: "forecast", label: "AI Forecast" },
                  { value: "research", label: "Research" },
                  { value: "fundamentals", label: "Fundamentals" },
                  { value: "options", label: "Options" },
                ].map((tab) => (
                  <Tabs.Trigger
                    key={tab.value}
                    value={tab.value}
                    className={cn(
                      "px-3 py-2.5 text-xs font-medium transition-colors border-b-2 border-transparent",
                      "data-[state=active]:border-nq-accent data-[state=active]:text-nq-accent",
                      "text-nq-text-tertiary hover:text-nq-text-secondary"
                    )}
                  >
                    {tab.label}
                  </Tabs.Trigger>
                ))}
              </Tabs.List>

              <Tabs.Content value="forecast" className="flex-1 overflow-y-auto p-4">
                <AiForecastTab symbol={symbol} />
              </Tabs.Content>
              <Tabs.Content value="research" className="flex-1 overflow-y-auto p-4">
                <div className="space-y-3">
                  <CardTitle>AI Research Report</CardTitle>
                  <div className="text-xs text-nq-text-secondary leading-relaxed space-y-2">
                    <p><strong className="text-nq-text-primary">Technical View:</strong> The stock is trading above all major moving averages with a bullish MACD crossover. RSI at 62 shows momentum without being overbought. Volume profile suggests accumulation near ₹2,800 support.</p>
                    <p><strong className="text-nq-text-primary">Fundamental View:</strong> Strong quarterly results with 12% YoY revenue growth. Jio continues to add subscribers, and retail arm showing improving margins. Fair value estimate: ₹3,100 (9% upside).</p>
                    <p><strong className="text-nq-text-primary">News Catalysts:</strong> Upcoming AGM expected to announce green energy capex plans. Analyst consensus remains BUY with average target ₹3,050.</p>
                    <p><strong className="text-nq-text-primary">Risk Factors:</strong> Rising crude oil prices could impact petrochemical margins. Global recession risk and potential rate hikes remain headwinds.</p>
                  </div>
                </div>
              </Tabs.Content>
              <Tabs.Content value="fundamentals" className="flex-1 overflow-y-auto p-4">
                <FundamentalsTab symbol={symbol} />
              </Tabs.Content>
              <Tabs.Content value="options" className="flex-1 overflow-y-auto p-4">
                <div className="space-y-3">
                  <CardTitle>Options Chain</CardTitle>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-[10px] text-nq-text-tertiary uppercase tracking-wider border-b border-nq-border pb-1">
                      <span>Strike</span><span>Call OI</span><span>Put OI</span><span>IV%</span>
                    </div>
                    {[2800, 2820, 2840, 2860, 2880, 2900].map((strike) => (
                      <div key={strike} className={cn(
                        "flex items-center justify-between font-mono text-xs py-1",
                        strike === 2840 ? "bg-nq-accent/5 rounded px-1 font-semibold" : ""
                      )}>
                        <span className="text-nq-text-primary">{strike}</span>
                        <span className="text-nq-bull">{(Math.random() * 500000 + 100000).toFixed(0)}</span>
                        <span className="text-nq-bear">{(Math.random() * 500000 + 100000).toFixed(0)}</span>
                        <span className="text-nq-warning">{(18 + Math.random() * 8).toFixed(1)}</span>
                      </div>
                    ))}
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t border-nq-border">
                    <div>
                      <span className="text-[10px] text-nq-text-tertiary">PCR</span>
                      <span className="ml-1 font-mono text-sm font-semibold text-nq-bull">0.82</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-nq-text-tertiary">Max Pain</span>
                      <span className="ml-1 font-mono text-sm font-semibold text-nq-warning">₹2,850</span>
                    </div>
                  </div>
                </div>
              </Tabs.Content>
            </Tabs.Root>
          </Card>
        </div>
      </div>
    </div>
  );
}
