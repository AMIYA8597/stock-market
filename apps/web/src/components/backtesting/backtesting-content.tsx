"use client";

import { useState } from "react";
import { Play, Download } from "lucide-react";
import { Card, CardHeader, CardTitle, Button, Input, StatCard, cn, formatPercent, getPriceColor } from "@neuroquant/ui";
import type { StrategyName } from "@neuroquant/types";

const STRATEGIES: { value: StrategyName; label: string }[] = [
  { value: "kalman_pairs", label: "Kalman Filter Pairs Trading" },
  { value: "adaptive_momentum", label: "Adaptive Momentum" },
  { value: "ml_alpha", label: "ML Alpha Strategy" },
  { value: "stat_arb", label: "Statistical Arbitrage" },
  { value: "volatility_regime", label: "Volatility Regime" },
  { value: "deep_rl", label: "Deep RL Agent (PPO)" },
];

const SAMPLE_METRICS = {
  cagr: 18.4, totalReturn: 42.8, sharpe: 1.62, sortino: 2.14, calmar: 1.89,
  maxDrawdown: -9.7, winRate: 58.2, profitFactor: 1.84, totalTrades: 247, avgHold: 8.4,
};

const MONTHLY_RETURNS = [
  { month: "Jan", pct: 3.2 }, { month: "Feb", pct: -1.4 }, { month: "Mar", pct: 4.1 },
  { month: "Apr", pct: 1.8 }, { month: "May", pct: -0.6 }, { month: "Jun", pct: 2.9 },
  { month: "Jul", pct: -2.1 }, { month: "Aug", pct: 3.7 }, { month: "Sep", pct: 1.2 },
  { month: "Oct", pct: 4.5 }, { month: "Nov", pct: -0.8 }, { month: "Dec", pct: 2.3 },
];

export function BacktestingContent() {
  const [strategy, setStrategy] = useState<StrategyName>("adaptive_momentum");
  const [isRunning, setIsRunning] = useState(false);
  const [hasResults, setHasResults] = useState(true);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl font-bold text-nq-text-primary">Research Lab — Backtesting</h1>
        {hasResults && (
          <Button variant="secondary" size="sm"><Download className="h-3.5 w-3.5" /> PDF Report</Button>
        )}
      </div>

      <div className="grid grid-cols-12 gap-4">
        {/* Config panel */}
        <div className="col-span-12 lg:col-span-3">
          <Card className="space-y-4">
            <CardTitle>Strategy Configuration</CardTitle>
            <div>
              <label className="text-[10px] text-nq-text-tertiary mb-1 block">Strategy</label>
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value as StrategyName)}
                className="w-full rounded-nq border border-nq-border bg-nq-bg-secondary px-3 py-1.5 text-xs text-nq-text-primary"
              >
                {STRATEGIES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[10px] text-nq-text-tertiary mb-1 block">Date Range</label>
              <div className="flex gap-2">
                <Input type="date" defaultValue="2020-01-01" className="h-7 text-[11px]" />
                <Input type="date" defaultValue="2024-12-31" className="h-7 text-[11px]" />
              </div>
            </div>
            <div>
              <label className="text-[10px] text-nq-text-tertiary mb-1 block">Initial Capital</label>
              <Input type="number" defaultValue="1000000" className="h-7 text-[11px]" />
            </div>
            <div>
              <label className="text-[10px] text-nq-text-tertiary mb-1 block">Benchmark</label>
              <select className="w-full rounded-nq border border-nq-border bg-nq-bg-secondary px-3 py-1.5 text-xs text-nq-text-primary">
                <option>Nifty 50</option><option>S&P 500</option><option>Buy & Hold</option>
              </select>
            </div>
            <div className="flex items-center gap-2">
              <input type="checkbox" defaultChecked className="rounded border-nq-border" />
              <span className="text-xs text-nq-text-secondary">Include transaction costs</span>
            </div>
            <Button className="w-full" loading={isRunning} onClick={() => { setIsRunning(true); setTimeout(() => { setIsRunning(false); setHasResults(true); }, 1500); }}>
              <Play className="h-3.5 w-3.5" /> Run Backtest
            </Button>
          </Card>
        </div>

        {/* Results */}
        <div className="col-span-12 lg:col-span-9 space-y-4">
          {hasResults && (
            <>
              {/* Headline metrics */}
              <div className="grid grid-cols-5 gap-3">
                <StatCard label="CAGR" value={`${SAMPLE_METRICS.cagr}%`} change={SAMPLE_METRICS.cagr} />
                <StatCard label="Sharpe" value={SAMPLE_METRICS.sharpe.toFixed(2)} change={SAMPLE_METRICS.sharpe > 1 ? 1 : -1} />
                <StatCard label="Max DD" value={`${SAMPLE_METRICS.maxDrawdown}%`} change={SAMPLE_METRICS.maxDrawdown} />
                <StatCard label="Win Rate" value={`${SAMPLE_METRICS.winRate}%`} change={SAMPLE_METRICS.winRate > 50 ? 1 : -1} />
                <StatCard label="Trades" value={SAMPLE_METRICS.totalTrades.toString()} />
              </div>

              {/* Monthly returns heatmap */}
              <Card>
                <CardHeader><CardTitle>Monthly Returns</CardTitle></CardHeader>
                <div className="flex gap-1.5">
                  {MONTHLY_RETURNS.map((m) => (
                    <div key={m.month} className="flex-1 text-center">
                      <div
                        className={cn("rounded py-3 text-xs font-mono font-medium", getPriceColor(m.pct))}
                        style={{
                          backgroundColor: m.pct >= 0
                            ? `rgba(0, 230, 118, ${Math.min(Math.abs(m.pct) / 5, 0.3)})`
                            : `rgba(255, 59, 59, ${Math.min(Math.abs(m.pct) / 5, 0.3)})`,
                        }}
                      >
                        {formatPercent(m.pct)}
                      </div>
                      <div className="text-[9px] text-nq-text-tertiary mt-1">{m.month}</div>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Significance tests */}
              <Card>
                <CardHeader><CardTitle>Statistical Significance</CardTitle></CardHeader>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <div className="text-[10px] text-nq-text-tertiary">MC p-value</div>
                    <div className="font-mono text-sm font-semibold text-nq-bull">0.012</div>
                    <div className="text-[9px] text-nq-text-tertiary">Significant at 5%</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-nq-text-tertiary">Bootstrap Sharpe CI</div>
                    <div className="font-mono text-sm font-semibold text-nq-text-primary">[1.12, 2.08]</div>
                    <div className="text-[9px] text-nq-text-tertiary">95% confidence</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-nq-text-tertiary">Deflated Sharpe</div>
                    <div className="font-mono text-sm font-semibold text-nq-bull">1.38</div>
                    <div className="text-[9px] text-nq-text-tertiary">Adjusted for trials</div>
                  </div>
                </div>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
