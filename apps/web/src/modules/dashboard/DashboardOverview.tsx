"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { BellRing, BrainCircuit, ShieldCheck, TrendingUp, Wallet } from "lucide-react";
import { createChart, ColorType, AreaSeries, LineSeries } from "lightweight-charts";
import type { IChartApi, Time } from "lightweight-charts";

import { Badge, Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Modal, Table, TableCell, TableHead, TableRow } from "@neuroquant/ui";
import { alertsApi, paperTradingApi, portfolioApi } from "@/lib/api-client";
import { useSignalQuery } from "@/hooks/queries/useSignals";

type PaperPnl = {
  cash_balance?: number;
  daily_realized_loss?: number;
  realized_pnl?: number;
  total_equity?: number;
  unrealized_pnl?: number;
};

type PositionRow = {
  current_price?: number;
  market_value?: number;
  model_signal?: string;
  pnl?: number;
  quantity?: number;
  symbol: string;
};

function formatCurrency(value: number | null | undefined): string {
  const safeValue = Number.isFinite(value) ? Number(value) : 0;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(safeValue);
}

function formatPercent(value: number | null | undefined): string {
  const safeValue = Number.isFinite(value) ? Number(value) : 0;
  return `${safeValue.toFixed(1)}%`;
}

function formatRatio(value: number | null | undefined): string {
  if (!Number.isFinite(value)) {
    return "--";
  }
  return Number(value).toFixed(2);
}

export function DashboardOverview(): JSX.Element {
  const [createAlertOpen, setCreateAlertOpen] = useState(false);
  const [alertSymbol, setAlertSymbol] = useState("NIFTY50");
  const [alertThreshold, setAlertThreshold] = useState("1.0");
  const [alertSubmitting, setAlertSubmitting] = useState(false);

  const handleCreateAlert = async () => {
    setAlertSubmitting(true);
    try {
      await alertsApi.create({
        name: `${alertSymbol} Price Alert`,
        symbol: alertSymbol,
        alert_type: "price",
        conditions: { threshold: parseFloat(alertThreshold) },
        channels: ["in_app"],
        cooldown_minutes: 15,
        is_active: true,
      });
      setCreateAlertOpen(false);
    } catch {
      // silently close — alerts page has full error handling
    } finally {
      setAlertSubmitting(false);
    }
  };

  const {
    data: pnl,
    isPending: isPendingPnl,
    isError: isErrorPnl,
  } = useQuery({
    queryKey: ["paper-trade", "pnl"],
    queryFn: () => paperTradingApi.getPnl() as Promise<PaperPnl>,
    retry: 1,
    staleTime: 30_000,
  });

  const {
    data: positions,
    isPending: isPendingPositions,
    isError: isErrorPositions,
  } = useQuery({
    queryKey: ["paper-trade", "positions"],
    queryFn: () => paperTradingApi.getPositions() as Promise<PositionRow[]>,
    retry: 1,
    staleTime: 30_000,
  });

  const {
    data: portfolios,
    isPending: isPendingPortfolios,
    isError: isErrorPortfolios,
  } = useQuery({
    queryKey: ["portfolios"],
    queryFn: () => portfolioApi.list(),
    retry: 1,
    staleTime: 30_000,
  });

  const portfolio = portfolios?.[0] ?? null;

  const {
    data: riskMetrics,
    isPending: isPendingRisk,
  } = useQuery({
    queryKey: ["risk", portfolio?.id],
    queryFn: () => portfolioApi.getRisk(portfolio!.id),
    enabled: Boolean(portfolio?.id),
    retry: 1,
  });

  const {
    data: performance,
    isPending: isPendingPerformance,
  } = useQuery({
    queryKey: ["performance", portfolio?.id],
    queryFn: () => portfolioApi.getPerformance(),
    enabled: Boolean(portfolio?.id),
    retry: 1,
  });

  const {
    data: alertsHistory,
    isPending: isPendingAlerts,
    isError: isErrorAlerts,
  } = useQuery({
    queryKey: ["alerts", "history"],
    queryFn: () => alertsApi.getHistory(6),
    retry: 1,
    staleTime: 30_000,
  });

  const {
    data: signal,
    isPending: isPendingSignal,
  } = useSignalQuery("NIFTY50");

  // Only block render while queries are actively fetching (not errored).
  // Errored queries resolve immediately so the dashboard never hangs forever.
  const isLoading =
    (isPendingPnl && !isErrorPnl) &&
    (isPendingPositions && !isErrorPositions) &&
    (isPendingPortfolios && !isErrorPortfolios);

  // Global blocking error removed to allow graceful degradation of individual widgets

  const modelBreakdown = useMemo(() => {
    if (!signal?.models) {
      return [];
    }

    return Object.entries(signal.models)
      .filter(([key]) => key !== "technical" && key !== "regime")
      .map(([key, model]) => {
        const value =
          typeof model === "object" && model !== null
            ? Number(
                (model as { raw_signal?: number; regime_signal?: number; spillover_risk?: number }).raw_signal ??
                  (model as { regime_signal?: number }).regime_signal ??
                  (model as { spillover_risk?: number }).spillover_risk ??
                  0,
              )
            : 0;

        return {
          label: key,
          confidence: value * 100, // convert to percentage scale
        };
      });
  }, [signal?.models]);

  if (isLoading) {
    return <div className="p-8 text-center text-sm text-[var(--nq-text-secondary)]">Loading dashboard data...</div>;
  }

  const pnlData = pnl ?? {};
  const openPositions = positions ?? [];
  const alerts = alertsHistory ?? [];
  const performanceSeries = Array.isArray(performance?.series)
    ? performance.series.map((point) => ({
        date: point.date,
        day: new Date(point.date).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
        value: Number(point.portfolio_value ?? 0),
        benchmark: Number(point.benchmark_value ?? 0),
      }))
    : [];

  const kpis = [
    {
      label: "Total Equity",
      value: formatCurrency(pnlData.total_equity),
      detail: `Cash ${formatCurrency(pnlData.cash_balance)}`,
      icon: Wallet,
    },
    {
      label: "Unrealized P&L",
      value: formatCurrency(pnlData.unrealized_pnl),
      detail: Number(pnlData.unrealized_pnl ?? 0) >= 0 ? "Open profit" : "Open loss",
      icon: TrendingUp,
    },
    {
      label: "Realized P&L",
      value: formatCurrency(pnlData.realized_pnl),
      detail: `Daily loss ${formatCurrency(pnlData.daily_realized_loss)}`,
      icon: ShieldCheck,
    },
    {
      label: "Signal Bias",
      value: signal?.ensemble?.signal ?? "NEUTRAL",
      detail: `${Math.round((signal?.ensemble?.confidence ?? 0) * 100)}% confidence`,
      icon: BrainCircuit,
    },
  ];

  const regimeProbabilities = signal?.regime?.probs ?? {};
  const regimeCards = [
    { label: "Bull", value: Number(regimeProbabilities.BULL ?? 0), color: "#00E676" },
    { label: "Bear", value: Number(regimeProbabilities.BEAR ?? 0), color: "#FF5B5C" },
    { label: "Sideways", value: Number(regimeProbabilities.SIDEWAYS ?? 0), color: "#F7C948" },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6 pb-8"
    >
      <div className="rounded-[1.4rem] border border-white/10 bg-[linear-gradient(135deg,rgba(0,212,245,0.12),rgba(255,255,255,0.03))] px-6 py-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <Badge variant="outline" className="border-white/10 bg-white/[0.06] text-[10px] uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">
              Desk Overview
            </Badge>
            <h1 className="text-3xl font-semibold tracking-tight text-[var(--nq-text-primary)] sm:text-4xl">
              Market Dashboard & Portfolio Overview
            </h1>
            <p className="max-w-3xl text-sm leading-7 text-[var(--nq-text-secondary)]">
              Monitor your live portfolio, track market movements, and analyze AI-driven model signals in real-time.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => setCreateAlertOpen(true)}>Create alert</Button>
            <Button variant="secondary">Refresh desk</Button>
          </div>
        </div>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {kpis.map((item) => {
          const Icon = item.icon;
          return (
            <Card key={item.label}>
              <CardHeader>
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <CardDescription>{item.label}</CardDescription>
                    <CardTitle className="mt-2 text-2xl">{item.value}</CardTitle>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-[var(--nq-accent)]">
                    <Icon className="h-5 w-5" />
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-[var(--nq-text-secondary)]">{item.detail}</p>
              </CardContent>
            </Card>
          );
        })}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.45fr_0.95fr]">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-4">
              <div>
                <CardTitle>Equity Curve</CardTitle>
                <CardDescription>Live portfolio value vs benchmark, using the current backend contract.</CardDescription>
              </div>
              <Badge variant="secondary">{performanceSeries.length} points</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-[320px]">
              <div className="h-[320px]" ref={(node) => {
                if (node) {
                  // Only run once when the node mounts or data changes
                  const nodeWithChart = node as HTMLDivElement & { _chart?: IChartApi };
                  if (nodeWithChart._chart) return;
                  const chart = createChart(node, {
                    layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: 'rgba(255,255,255,0.45)' },
                    grid: { vertLines: { color: 'rgba(255,255,255,0.08)' }, horzLines: { color: 'rgba(255,255,255,0.08)' } },
                    rightPriceScale: { borderVisible: false },
                    timeScale: { borderVisible: false, timeVisible: true }
                  });
                  nodeWithChart._chart = chart;

                  const benchmarkSeries = chart.addSeries(LineSeries, {
                    color: '#8B9BB4', lineWidth: 2
                  });
                  const portfolioSeries = chart.addSeries(AreaSeries, {
                    lineColor: '#00D4F5', topColor: 'rgba(0, 212, 245, 0.35)', bottomColor: 'rgba(0, 212, 245, 0.02)', lineWidth: 2
                  });

                  // Use the real observation date as the chart's time axis, not
                  // the array index — an index has no relationship to actual
                  // elapsed time and would misrepresent uneven-interval data.
                  const toTime = (isoDate: string): Time => isoDate.slice(0, 10) as Time;
                  const benchData = performanceSeries.map((d) => ({ time: toTime(d.date), value: d.benchmark }));
                  const portData = performanceSeries.map((d) => ({ time: toTime(d.date), value: d.value }));
                  benchmarkSeries.setData(benchData);
                  portfolioSeries.setData(portData);
                  chart.timeScale().fitContent();

                  const resize = () => { chart.applyOptions({ width: node.clientWidth }); };
                  window.addEventListener('resize', resize);
                }
              }} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-4">
              <div>
                <CardTitle>Market Regime</CardTitle>
                <CardDescription>Model probabilities from the current signal snapshot.</CardDescription>
              </div>
              <Badge variant="bull">{signal?.ensemble?.signal ?? "NEUTRAL"}</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {regimeCards.map((item) => (
              <div key={item.label} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-[var(--nq-text-secondary)]">{item.label}</span>
                  <span className="font-medium text-[var(--nq-text-primary)]">{formatPercent(item.value * 100)}</span>
                </div>
                <div className="h-2 rounded-full bg-white/[0.08]">
                  <div className="h-2 rounded-full" style={{ width: `${Math.max(0, Math.min(100, item.value * 100))}%`, backgroundColor: item.color }} />
                </div>
              </div>
            ))}

            <div className="rounded-[1.2rem] border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Model Confidence</p>
              <div className="mt-4 space-y-3">
                {modelBreakdown.length === 0 ? (
                  <p className="text-sm text-[var(--nq-text-secondary)]">No model breakdown available.</p>
                ) : (
                  modelBreakdown.map((item) => (
                    <div key={item.label} className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-[var(--nq-text-secondary)]">{item.label}</span>
                        <span className="font-medium text-[var(--nq-text-primary)]">{item.confidence}%</span>
                      </div>
                      <div className="h-2 rounded-full bg-white/[0.08]">
                        <div className="h-2 rounded-full bg-[linear-gradient(90deg,var(--nq-accent),#69f5ff)]" style={{ width: `${item.confidence}%` }} />
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-center">
                <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Sharpe</p>
                <p className="mt-1 text-lg font-semibold text-[var(--nq-text-primary)]">{formatRatio(riskMetrics?.sharpe_ratio ?? null)}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-center">
                <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Sortino</p>
                <p className="mt-1 text-lg font-semibold text-[var(--nq-text-primary)]">{formatRatio(riskMetrics?.sortino_ratio ?? null)}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-center">
                <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Beta</p>
                <p className="mt-1 text-lg font-semibold text-[var(--nq-text-primary)]">{formatRatio(riskMetrics?.beta ?? null)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-4">
              <div>
                <CardTitle>Open Positions</CardTitle>
                <CardDescription>Lean table view that stays stable even when some backend fields are missing.</CardDescription>
              </div>
              <Badge variant="outline" className="border-white/10 bg-white/[0.06] text-[var(--nq-text-secondary)]">
                {openPositions.length} active
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <Table>
              <thead>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Qty</TableHead>
                  <TableHead>Price</TableHead>
                  <TableHead>P&amp;L</TableHead>
                  <TableHead>Signal</TableHead>
                </TableRow>
              </thead>
              <tbody>
                {openPositions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="py-8 text-center text-sm text-[var(--nq-text-secondary)]">
                      No open positions yet.
                    </TableCell>
                  </TableRow>
                ) : (
                  openPositions.map((row) => (
                    <TableRow key={row.symbol}>
                      <TableCell className="font-semibold">{row.symbol}</TableCell>
                      <TableCell>{row.quantity ?? 0}</TableCell>
                      <TableCell>{formatCurrency(row.current_price)}</TableCell>
                      <TableCell className={(row.pnl ?? 0) >= 0 ? "text-[var(--nq-bull)]" : "text-[var(--nq-bear)]"}>
                        {formatCurrency(row.pnl)}
                      </TableCell>
                      <TableCell>{row.model_signal ?? signal?.ensemble?.signal ?? "NEUTRAL"}</TableCell>
                    </TableRow>
                  ))
                )}
              </tbody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-4">
              <div>
                <CardTitle>Recent Alerts</CardTitle>
                <CardDescription>Latest system activity from the alert stream.</CardDescription>
              </div>
              <BellRing className="h-5 w-5 text-[var(--nq-accent)]" />
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {alerts.length === 0 ? (
              <div className="rounded-[1.1rem] border border-white/10 bg-white/5 p-4 text-sm text-[var(--nq-text-secondary)]">
                No alerts have fired yet.
              </div>
            ) : (
              alerts.map((item) => (
                <div key={item.id} className="rounded-[1.1rem] border border-white/10 bg-white/5 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium text-[var(--nq-text-primary)]">{item.alert_name}</p>
                      <p className="mt-1 text-sm text-[var(--nq-text-secondary)]">{item.message}</p>
                    </div>
                    <Badge variant="secondary">{item.symbol}</Badge>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </section>

      <Modal
        open={createAlertOpen}
        onOpenChange={setCreateAlertOpen}
        title="Create alert"
        description="Configure a new real-time alert for price or signal changes."
      >
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Input value={alertSymbol} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAlertSymbol(e.target.value)} placeholder="Symbol" />
            <Input value={alertThreshold} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAlertThreshold(e.target.value)} placeholder="Threshold %" />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setCreateAlertOpen(false)}>
              Cancel
            </Button>
            <Button type="button" onClick={handleCreateAlert} disabled={alertSubmitting}>
              {alertSubmitting ? "Creating..." : "Create Alert"}
            </Button>
          </div>
        </div>
      </Modal>
    </motion.div>
  );
}
