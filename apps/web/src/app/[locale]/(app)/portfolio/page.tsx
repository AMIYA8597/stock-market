/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { paperTradingApi, portfolioApi } from "@/lib/api-client";
import { usePriceFeed } from "@/hooks/usePriceFeed";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, Line, PieChart, Pie, Cell } from "recharts";

const CURRENCY_FORMATTER = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 2,
  minimumFractionDigits: 2,
});

const PERCENT_FORMATTER = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 2,
  minimumFractionDigits: 2,
});

function formatMoney(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return `₹${CURRENCY_FORMATTER.format(value)}`;
}

const COLORS = ["#00E676", "#FF3B5C", "#00D4F5", "#F7C948", "#8B5CF6", "#69f5ff"];

export default function PortfolioPage(): JSX.Element {
  const [activeTab, setActiveTab] = useState<"holdings" | "performance">("holdings");

  // Load paper trading data
  const { data: pnl, isLoading: isLoadingPnl, isError: isErrorPnl } = useQuery({ queryKey: ["paper-trade", "pnl"], queryFn: () => paperTradingApi.getPnl() });
  const { data: positions, isLoading: isLoadingPositions, isError: isErrorPositions } = useQuery({ queryKey: ["paper-trade", "positions"], queryFn: () => paperTradingApi.getPositions() });
  
  // Load portfolio performance for equity curve
  const { data: portfolios } = useQuery({ queryKey: ["portfolios"], queryFn: () => portfolioApi.list() });
  const portfolioId = portfolios?.[0]?.id;
  const { data: performance, isLoading: isLoadingPerf } = useQuery({ queryKey: ["performance", portfolioId], queryFn: () => portfolioApi.getPerformance(), enabled: !!portfolioId });
  const { data: riskMetrics } = useQuery({ queryKey: ["risk", portfolioId], queryFn: () => portfolioApi.getRisk(portfolioId!), enabled: !!portfolioId });

  const pnlData = pnl as any;
  const positionsData = (positions as any[]) || [];

  // Setup live prices via websocket
  const symbols = useMemo(() => positionsData.map((h) => h.symbol.toUpperCase()), [positionsData]);
  const { ticks, status } = usePriceFeed(symbols);

  // isLoadingPerf is gated by `enabled: !!portfolioId`; a disabled query never leaves
  // "pending", so only block on it once actually enabled or this hangs forever pre-portfolio.
  const isLoading = isLoadingPnl || isLoadingPositions || (Boolean(portfolioId) && isLoadingPerf);
  const error = isErrorPnl || isErrorPositions ? "Unable to load portfolio data." : null;

  // Calculate live valuations
  const portfolioValue = pnlData?.total_equity;
  const totalUnrealized = pnlData?.unrealized_pnl;

  const equitySeries = performance?.series ? performance.series.map((p: any) => ({
    day: new Date(p.date).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    equity: Number(p.portfolio_value),
    benchmark: Number(p.benchmark_value),
  })) : [];

  const allocationSeries = positionsData.map((h: any) => ({ name: h.symbol, value: h.quantity * h.current_price }));

  return (
    <main className="min-h-screen bg-[var(--nq-bg-base)] p-6 text-[var(--nq-text-primary)]">
      <h1 className="mb-2 text-2xl font-semibold">Portfolio Workspace</h1>
      <div className="mb-4 flex items-center justify-between gap-3 flex-wrap">
        <p className="text-xs text-[var(--nq-text-secondary)]">
          Manage positions, holdings, and risk. Price feed status: {status}.
        </p>
        <div className="flex items-center gap-2">
          <Link
            href="/portfolio/funds"
            className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-3 md:py-1.5 min-h-[44px] md:min-h-0 text-xs text-[var(--nq-text-secondary)] hover:border-[var(--nq-border-hover)] inline-flex items-center"
          >
            Manage funds
          </Link>
          <Link
            href="/portfolio/orders"
            className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-3 md:py-1.5 min-h-[44px] md:min-h-0 text-xs text-[var(--nq-text-secondary)] hover:border-[var(--nq-border-hover)] inline-flex items-center"
          >
            Order history
          </Link>
          <Link
            href="/portfolio/optimizer"
            className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-3 md:py-1.5 min-h-[44px] md:min-h-0 text-xs text-[var(--nq-text-secondary)] hover:border-[var(--nq-border-hover)] inline-flex items-center"
          >
            Optimizer
          </Link>
        </div>
      </div>
      {error ? <p className="mb-2 text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      {/* Overview Cards */}
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Portfolio Equity", formatMoney(portfolioValue)],
          ["Cash Balance", formatMoney(pnlData?.cash_balance)],
          ["Unrealized PnL", formatMoney(totalUnrealized)],
          ["Beta Score", typeof riskMetrics?.beta === "number" ? riskMetrics.beta.toFixed(2) : "--"],
        ].map(([key, value]) => (
          <div key={key} className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3">
            <div className="text-xs text-[var(--nq-text-secondary)]">{key}</div>
            <div className="mt-1 text-sm font-semibold">{value}</div>
          </div>
        ))}
      </section>

      {/* Tabs Row */}
      <div className="mt-6 flex border-b border-[var(--nq-border)] gap-6 text-sm font-medium overflow-x-auto custom-scrollbar">
        <button
          onClick={() => setActiveTab("holdings")}
          className={`py-3 md:pb-2.5 md:pt-0 min-h-[44px] md:min-h-0 whitespace-nowrap transition border-b-2 ${
            activeTab === "holdings"
              ? "border-[var(--nq-accent-cyan)] text-[var(--nq-text-primary)]"
              : "border-transparent text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)]"
          }`}
        >
          Holdings & Allocation
        </button>
        <button
          onClick={() => setActiveTab("performance")}
          className={`py-3 md:pb-2.5 md:pt-0 min-h-[44px] md:min-h-0 whitespace-nowrap transition border-b-2 ${
            activeTab === "performance"
              ? "border-[var(--nq-accent-cyan)] text-[var(--nq-text-primary)]"
              : "border-transparent text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)]"
          }`}
        >
          Equity Curve
        </button>
      </div>

      <div className="mt-6">
        {isLoading ? (
          <div className="py-12 text-center text-sm text-[var(--nq-text-secondary)]">Loading...</div>
        ) : activeTab === "holdings" ? (
          <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
            {/* Holdings Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="border-b border-[var(--nq-border)]">
                    <th className="pb-2 font-medium text-[var(--nq-text-secondary)] font-mono uppercase text-xs tracking-wider">Symbol</th>
                    <th className="pb-2 font-medium text-[var(--nq-text-secondary)] font-mono uppercase text-xs tracking-wider text-right">Qty</th>
                    <th className="pb-2 font-medium text-[var(--nq-text-secondary)] font-mono uppercase text-xs tracking-wider text-right">Avg Price</th>
                    <th className="pb-2 font-medium text-[var(--nq-text-secondary)] font-mono uppercase text-xs tracking-wider text-right">LTP</th>
                    <th className="pb-2 font-medium text-[var(--nq-text-secondary)] font-mono uppercase text-xs tracking-wider text-right">Unrealized</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--nq-border)]">
                  {positionsData.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-[var(--nq-text-muted)]">No active holdings.</td>
                    </tr>
                  ) : (
                    positionsData.map((pos) => {
                      const livePrice = ticks.get(pos.symbol)?.price ?? pos.current_price;
                      const unrealized = (livePrice - pos.avg_buy_price) * pos.quantity;
                      const isProfit = unrealized >= 0;
                      return (
                        <tr key={pos.symbol} className="hover:bg-[rgba(255,255,255,0.02)]">
                          <td className="py-3 font-medium">{pos.symbol}</td>
                          <td className="py-3 text-right">{pos.quantity}</td>
                          <td className="py-3 text-right font-mono text-xs">{formatMoney(pos.avg_buy_price)}</td>
                          <td className="py-3 text-right font-mono text-xs">{formatMoney(livePrice)}</td>
                          <td className={`py-3 text-right font-mono text-xs ${isProfit ? 'text-[var(--nq-bull)]' : 'text-[var(--nq-bear)]'}`}>
                            {isProfit ? '+' : ''}{formatMoney(unrealized)}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* Allocation Donut */}
            <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
              <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-[var(--nq-text-secondary)]">Allocation</h3>
              {allocationSeries.length > 0 ? (
                <div className="h-[200px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Tooltip contentStyle={{ background: "rgba(12, 16, 24, 0.96)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }} />
                      <Pie data={allocationSeries} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={2}>
                        {allocationSeries.map((entry, index) => (
                          <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="flex h-[200px] items-center justify-center text-sm text-[var(--nq-text-muted)]">No allocation data</div>
              )}
            </div>
          </div>
        ) : (
          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
             <h3 className="mb-4 text-xs font-semibold uppercase tracking-wider text-[var(--nq-text-secondary)]">Equity Curve</h3>
             <div className="h-[400px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={equitySeries}>
                    <defs>
                      <linearGradient id="equityFillCurve" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#00D4F5" stopOpacity={0.4} />
                        <stop offset="100%" stopColor="#00D4F5" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    {equitySeries.length === 0 && (
                        <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle" fill="rgba(255,255,255,0.45)" fontSize={14}>
                          Performance history unavailable
                        </text>
                    )}
                    <CartesianGrid stroke="rgba(255,255,255,0.05)" strokeDasharray="3 3" />
                    <XAxis dataKey="day" stroke="rgba(255,255,255,0.3)" fontSize={11} />
                    <YAxis stroke="rgba(255,255,255,0.3)" fontSize={11} domain={['auto', 'auto']} />
                    <Tooltip contentStyle={{ background: "rgba(12, 16, 24, 0.96)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8 }} />
                    <Area type="monotone" dataKey="equity" stroke="#00D4F5" strokeWidth={2} fill="url(#equityFillCurve)" />
                    <Line type="monotone" dataKey="benchmark" stroke="#8B5CF6" strokeWidth={1.5} dot={false} strokeDasharray="4 4" />
                  </AreaChart>
                </ResponsiveContainer>
             </div>
          </div>
        )}
      </div>
    </main>
  );
}
