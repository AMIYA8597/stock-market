"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  ArrowRight,
  BarChart3,
  BellRing,
  BrainCircuit,
  Download,
  Eye,
  Gauge,
  LineChart,
  Megaphone,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Workflow,
  Zap,
} from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { Table, TableCell, TableHead, TableRow } from "@/components/ui/Table";
import { Button, Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle, StatCard } from "@/components/dashboard/premium";

const kpis = [
  { title: "Net asset value", value: "$18.42M", delta: "+2.8%", trend: "up" as const, icon: TrendingUp },
  { title: "Open signals", value: "17", delta: "+5 today", trend: "up" as const, icon: Sparkles },
  { title: "Risk utilization", value: "68%", delta: "-4.2%", trend: "down" as const, icon: Gauge },
  { title: "Execution latency", value: "42ms", delta: "-11ms", trend: "down" as const, icon: Zap },
] as const;

const equitySeries = [
  { day: "Mon", equity: 220, benchmark: 205, drawdown: 11 },
  { day: "Tue", equity: 246, benchmark: 211, drawdown: 9 },
  { day: "Wed", equity: 238, benchmark: 218, drawdown: 12 },
  { day: "Thu", equity: 272, benchmark: 226, drawdown: 8 },
  { day: "Fri", equity: 286, benchmark: 231, drawdown: 6 },
  { day: "Sat", equity: 274, benchmark: 233, drawdown: 7 },
  { day: "Sun", equity: 301, benchmark: 238, drawdown: 4 },
];

const allocationSeries = [
  { name: "Equities", value: 48, color: "#00D4F5" },
  { name: "Options", value: 18, color: "#00E676" },
  { name: "Cash", value: 22, color: "#8B5CF6" },
  { name: "Hedges", value: 12, color: "#FFB800" },
];

const modelSignals = [
  { label: "Confidence", value: 92, tone: "text-[var(--nq-bull)]" },
  { label: "Volatility", value: 24, tone: "text-[var(--nq-warning)]" },
  { label: "Exposure", value: 68, tone: "text-[var(--nq-accent)]" },
];

const regimeScores = [
  { label: "BULL", value: 61, color: "#00E676" },
  { label: "BEAR", value: 11, color: "#FF3B5C" },
  { label: "SIDEWAYS", value: 19, color: "#FFB800" },
  { label: "CRISIS", value: 9, color: "#8B5CF6" },
] as const;

const [bullRegime, bearRegime, sideRegime] = regimeScores;

const activityFeed = [
  { id: "evt-1", icon: BellRing, title: "AAPL alert fired", description: "Intraday breakout crossed the live threshold.", time: "2m" },
  { id: "evt-2", icon: BrainCircuit, title: "Ensemble refreshed", description: "TFT and GNN weights rebalanced after the latest bar.", time: "12m" },
  { id: "evt-3", icon: ShieldCheck, title: "Risk scan passed", description: "No sector or leverage breaches detected in the book.", time: "31m" },
  { id: "evt-4", icon: Megaphone, title: "News sentiment flipped", description: "FinBERT score moved to positive on the semiconductor basket.", time: "54m" },
];

const openPositions = [
  { symbol: "AAPL", side: "Long", quantity: "420", pnl: "+$12,440", exposure: "$78,900" },
  { symbol: "NVDA", side: "Long", quantity: "108", pnl: "+$9,188", exposure: "$54,210" },
  { symbol: "TSLA", side: "Long", quantity: "190", pnl: "-$1,074", exposure: "$43,620" },
  { symbol: "MSFT", side: "Long", quantity: "210", pnl: "+$3,904", exposure: "$64,880" },
  { symbol: "AMZN", side: "Long", quantity: "330", pnl: "+$5,217", exposure: "$58,110" },
];

const quickActions = [
  { icon: BellRing, title: "Create alert", description: "Trigger breakout, range, or drift rules." },
  { icon: Workflow, title: "Run rebalance", description: "Rescale sleeves by current regime state." },
  { icon: Download, title: "Export report", description: "Download a clean CSV or PDF snapshot." },
  { icon: Eye, title: "Preview signal stack", description: "Inspect model consensus and regime bias." },
];

const newsFeed = [
  { source: "Reuters", headline: "Semiconductor names extend gains into the session", tone: "bull" as const },
  { source: "Bloomberg", headline: "Market breadth improves as risk appetite broadens", tone: "bull" as const },
  { source: "WSJ", headline: "Rates remain in focus ahead of upcoming guidance", tone: "neutral" as const },
  { source: "FinBERT", headline: "High-confidence positive sentiment on megacap software", tone: "bull" as const },
];

const signalGradient = ["#00D4F5", "#00E676", "#8B5CF6", "#FFB800"];

function scoreLabel(score: number): string {
  return `${score.toString().padStart(2, "0")}%`;
}

export function DashboardOverview(): JSX.Element {
  const [createAlertOpen, setCreateAlertOpen] = useState(false);

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }} className="space-y-6 pb-8">
      {/* QuantEdge Academic Disclaimer Banner */}
      <div className="rounded-lg border border-[rgba(239,68,68,0.25)] bg-[rgba(239,68,68,0.08)] p-3 text-center text-xs text-[#FF5A60] font-mono">
        <span className="font-bold uppercase mr-2">Academic Research Output:</span>
        Research output only, not investment advice. Data may be delayed. All signals are paper-trading suggestions.
      </div>

      <section className="grid gap-6 xl:grid-cols-[1.35fr_0.85fr]">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }}>
          <Card interactive glow className="relative overflow-hidden px-6 py-6 sm:px-8">
            <div className="absolute inset-0 bg-[radial-gradient(1200px_520px_at_0%_0%,rgba(0,212,245,0.16),transparent_42%),radial-gradient(900px_420px_at_100%_0%,rgba(139,92,246,0.14),transparent_42%),linear-gradient(180deg,rgba(255,255,255,0.03),transparent_38%)]" />
            <div className="relative grid gap-8 xl:grid-cols-[1.1fr_0.9fr] xl:items-start">
              <div className="space-y-6">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="bull" className="px-3 py-1.5 text-[10px] uppercase tracking-[0.16em]">
                    Live market state
                  </Badge>
                  <Badge variant="outline" className="px-3 py-1.5 text-[10px] uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">
                    Terminal ready
                  </Badge>
                  <Badge variant="secondary" className="px-3 py-1.5 text-[10px] uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">
                    Desk synced 30s ago
                  </Badge>
                </div>

                <div className="max-w-3xl space-y-4">
                  <h1 className="text-4xl font-semibold tracking-tight text-[var(--nq-text-primary)] sm:text-5xl xl:text-6xl">
                    A premium trading cockpit for signals, risk, and execution.
                  </h1>
                  <p className="max-w-2xl text-sm leading-7 text-[var(--nq-text-secondary)] sm:text-base">
                    Clean hierarchy, strong contrast, and responsive composition built for local verification. The layout keeps the market state, portfolio health, and model output visible without crowding the screen.
                  </p>
                </div>

                <div className="flex flex-wrap gap-3">
                  <Button leftIcon={<Sparkles className="h-4 w-4" />} onClick={() => setCreateAlertOpen(true)}>
                    Create alert
                  </Button>
                  <Button variant="secondary" leftIcon={<BarChart3 className="h-4 w-4" />}>
                    Rebalance sleeve
                  </Button>
                  <Button variant="ghost" leftIcon={<Eye className="h-4 w-4" />}>
                    Preview signal stack
                  </Button>
                </div>

                <div className="grid gap-3 sm:grid-cols-3">
                  {[
                    { label: "Uptime", value: "99.98%", detail: "No interruptions in 30 days." },
                    { label: "Net edge", value: "+14.8%", detail: "System alpha across core sleeves." },
                    { label: "Open signals", value: "17", detail: "3 high-conviction setups are actionable." },
                  ].map((item) => (
                    <div key={item.label} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                      <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">{item.label}</p>
                      <p className="mt-2 text-xl font-semibold tracking-tight text-[var(--nq-text-primary)]">{item.value}</p>
                      <p className="mt-1 text-xs text-[var(--nq-text-secondary)]">{item.detail}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid gap-4">
                <div className="rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.09),rgba(255,255,255,0.03))] p-5 shadow-[0_20px_50px_rgba(0,0,0,0.18)]">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Model snapshot</p>
                      <p className="mt-1 text-lg font-semibold text-[var(--nq-text-primary)]">Next best action</p>
                    </div>
                    <Badge variant="buy">Bullish</Badge>
                  </div>

                  <div className="mt-5 grid gap-5 sm:grid-cols-[0.92fr_1.08fr]">
                    <div className="flex items-center justify-center">
                      <div className="relative flex h-36 w-36 items-center justify-center rounded-full border border-white/10 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.12),rgba(255,255,255,0.02)_58%,transparent_60%)]">
                        <div
                          className="absolute inset-0 rounded-full"
                          style={{ background: `conic-gradient(var(--nq-accent) 0% 92%, rgba(255,255,255,0.08) 92% 100%)` }}
                        />
                        <div className="relative flex h-[7.5rem] w-[7.5rem] flex-col items-center justify-center rounded-full border border-white/10 bg-[var(--nq-bg-surface)] text-center shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]">
                          <span className="text-[10px] uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">Confidence</span>
                          <span className="mt-1 text-3xl font-semibold text-[var(--nq-text-primary)]">92%</span>
                          <span className="mt-1 text-[11px] text-[var(--nq-text-secondary)]">High conviction</span>
                        </div>
                      </div>
                    </div>

                    <div className="space-y-4">
                      {modelSignals.map((signal) => (
                        <div key={signal.label} className="space-y-2">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-[var(--nq-text-secondary)]">{signal.label}</span>
                            <span className={signal.tone}>{signal.value}%</span>
                          </div>
                          <div className="h-2 rounded-full bg-white/[0.08]">
                            <div className="h-2 rounded-full bg-[linear-gradient(90deg,var(--nq-accent),#69f5ff)]" style={{ width: `${signal.value}%` }} />
                          </div>
                        </div>
                      ))}

                      <div className="rounded-2xl border border-white/10 bg-[linear-gradient(135deg,rgba(0,230,118,0.14),rgba(255,255,255,0.05))] p-4">
                        <div className="flex items-center justify-between gap-4">
                          <div>
                            <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Regime</p>
                            <p className="mt-1 text-lg font-semibold text-[var(--nq-text-primary)]">Risk-on expansion</p>
                          </div>
                          <div className="rounded-full bg-[rgba(0,230,118,0.16)] px-3 py-1 text-xs font-semibold text-[var(--nq-bull)]">
                            Stable
                          </div>
                        </div>
                        <div className="mt-4 grid gap-2">
                          <div className="grid grid-cols-[72px_1fr] items-center gap-3 text-[11px] uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">
                            <span>Bull</span>
                            <div className="h-2 overflow-hidden rounded-full bg-white/[0.08]"><div className="h-2 rounded-full bg-[#00E676]" style={{ width: `${regimeScores[0].value}%` }} /></div>
                            <div className="h-2 overflow-hidden rounded-full bg-white/[0.08]"><div className="h-2 rounded-full bg-[#00E676]" style={{ width: `${bullRegime.value}%` }} /></div>
                          </div>
                          <div className="grid grid-cols-[72px_1fr] items-center gap-3 text-[11px] uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">
                            <span>Bear</span>
                            <div className="h-2 overflow-hidden rounded-full bg-white/[0.08]"><div className="h-2 rounded-full bg-[#FF3B5C]" style={{ width: `${bearRegime.value}%` }} /></div>
                          </div>
                          <div className="grid grid-cols-[72px_1fr] items-center gap-3 text-[11px] uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">
                            <span>Side</span>
                            <div className="h-2 overflow-hidden rounded-full bg-white/[0.08]"><div className="h-2 rounded-full bg-[#FFB800]" style={{ width: `${sideRegime.value}%` }} /></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 grid grid-cols-3 gap-3">
                    {[
                      { label: "Latency", value: "42ms" },
                      { label: "Drawdown", value: "1.8%" },
                      { label: "Coverage", value: "94%" },
                    ].map((item) => (
                      <div key={item.label} className="rounded-2xl border border-white/10 bg-white/5 p-3 text-center">
                        <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">{item.label}</p>
                        <p className="mt-1 text-base font-semibold text-[var(--nq-text-primary)]">{item.value}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: "Market", value: "Open" },
                    { label: "Calendar", value: "FOMC + 2d" },
                    { label: "Risk budget", value: "68% used" },
                  ].map((item) => (
                    <div key={item.label} className="rounded-2xl border border-white/10 bg-white/5 p-3 text-center">
                      <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">{item.label}</p>
                      <p className="mt-1 text-sm font-semibold text-[var(--nq-text-primary)]">{item.value}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Card>
        </motion.div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {kpis.map((item) => (
          <StatCard key={item.title} title={item.title} value={item.value} delta={item.delta} trend={item.trend} icon={item.icon} />
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, delay: 0.08 }}>
          <Card className="h-full">
            <CardHeader>
              <div>
                <CardTitle>Performance and regime map</CardTitle>
                <CardDescription>Equity curve, benchmark, and drawdown profile rendered in a clean, readable panel.</CardDescription>
              </div>
              <Badge variant="outline" className="border-white/10 bg-white/[0.06] text-[10px] uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">
                7D live
              </Badge>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
                  <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Alpha</p>
                  <p className="mt-1 text-xl font-semibold">+2.3%</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
                  <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Sharpe</p>
                  <p className="mt-1 text-xl font-semibold">1.84</p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
                  <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Win rate</p>
                  <p className="mt-1 text-xl font-semibold">74%</p>
                </div>
              </div>

              <div className="grid gap-4 lg:grid-cols-[1.35fr_0.9fr]">
                <div className="min-h-[320px] rounded-[1.25rem] border border-white/10 bg-[rgba(255,255,255,0.04)] p-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={equitySeries}>
                      <defs>
                        <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#00D4F5" stopOpacity={0.45} />
                          <stop offset="100%" stopColor="#00D4F5" stopOpacity={0.04} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />
                      <XAxis dataKey="day" stroke="rgba(255,255,255,0.45)" fontSize={11} />
                      <YAxis stroke="rgba(255,255,255,0.45)" fontSize={11} />
                      <Tooltip contentStyle={{ background: "rgba(12, 16, 24, 0.96)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 16 }} />
                      <Area type="monotone" dataKey="equity" stroke="#00D4F5" strokeWidth={2.5} fill="url(#equityFill)" />
                      <Line type="monotone" dataKey="benchmark" stroke="#8B5CF6" strokeWidth={2} dot={false} strokeDasharray="5 5" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>

                <div className="space-y-4">
                  <div className="min-h-[174px] rounded-[1.25rem] border border-white/10 bg-[rgba(255,255,255,0.04)] p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Allocation</p>
                        <p className="mt-1 text-lg font-semibold text-[var(--nq-text-primary)]">Sleeve mix</p>
                      </div>
                      <Badge variant="secondary">Balanced</Badge>
                    </div>

                    <div className="mt-3 h-[120px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Tooltip contentStyle={{ background: "rgba(12, 16, 24, 0.96)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 16 }} />
                          <Pie data={allocationSeries} dataKey="value" nameKey="name" innerRadius={40} outerRadius={58} paddingAngle={4}>
                            {allocationSeries.map((entry) => (
                              <Cell key={entry.name} fill={entry.color} />
                            ))}
                          </Pie>
                        </PieChart>
                      </ResponsiveContainer>
                    </div>

                    <div className="mt-3 space-y-2">
                      {allocationSeries.map((entry) => (
                        <div key={entry.name} className="flex items-center justify-between text-sm">
                          <span className="inline-flex items-center gap-2 text-[var(--nq-text-secondary)]">
                            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: entry.color }} />
                            {entry.name}
                          </span>
                          <span className="font-medium text-[var(--nq-text-primary)]">{entry.value}%</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-[1.25rem] border border-white/10 bg-[rgba(255,255,255,0.04)] p-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Risk curve</p>
                        <p className="mt-1 text-lg font-semibold text-[var(--nq-text-primary)]">Drawdown pressure</p>
                      </div>
                      <LineChart className="h-4 w-4 text-[var(--nq-text-secondary)]" />
                    </div>
                    <div className="mt-4 h-[120px]">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={equitySeries}>
                          <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />
                          <XAxis dataKey="day" stroke="rgba(255,255,255,0.45)" fontSize={11} />
                          <YAxis stroke="rgba(255,255,255,0.45)" fontSize={11} />
                          <Tooltip contentStyle={{ background: "rgba(12, 16, 24, 0.96)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 16 }} />
                          <Bar dataKey="drawdown" radius={[10, 10, 0, 0]}>
                            {equitySeries.map((entry, index) => (
                              <Cell key={entry.day} fill={signalGradient[index % signalGradient.length]} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 0.999, y: 0 }} transition={{ duration: 0.45, delay: 0.12 }} className="space-y-6">
          <Card>
            <CardHeader>
              <div>
                <CardTitle>Signal console</CardTitle>
                <CardDescription>Model consensus, regime state, and live news in one compact column.</CardDescription>
              </div>
              <Badge variant="outline" className="border-white/10 bg-white/[0.06] text-[10px] uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">
                Focus mode
              </Badge>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="rounded-[1.35rem] border border-white/10 bg-[linear-gradient(135deg,rgba(0,212,245,0.12),rgba(255,255,255,0.04))] p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Ensemble signal</p>
                    <p className="mt-1 text-2xl font-semibold text-[var(--nq-text-primary)]">BUY</p>
                  </div>
                  <div className="rounded-full bg-[rgba(0,230,118,0.16)] px-3 py-1 text-xs font-semibold text-[var(--nq-bull)]">
                    92% confidence
                  </div>
                </div>

                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
                    <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Kelly fraction</p>
                    <p className="mt-1 text-lg font-semibold text-[var(--nq-text-primary)]">12.4%</p>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
                    <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Regime</p>
                    <p className="mt-1 text-lg font-semibold text-[var(--nq-text-primary)]">Bull expansion</p>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                {regimeScores.map((item) => (
                  <div key={item.label} className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-[var(--nq-text-secondary)]">{item.label}</span>
                      <span className="font-medium text-[var(--nq-text-primary)]">{scoreLabel(item.value)}</span>
                    </div>
                    <div className="h-2 rounded-full bg-white/[0.08]">
                      <div className="h-2 rounded-full" style={{ width: `${item.value}%`, backgroundColor: item.color }} />
                    </div>
                  </div>
                ))}
              </div>

              <div className="rounded-[1.25rem] border border-white/10 bg-white/[0.04] p-4">
                <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Model weights</p>
                <div className="mt-4 space-y-3">
                  {[
                    { name: "TFT", weight: 32 },
                    { name: "HMM-GARCH", weight: 18 },
                    { name: "GNN", weight: 20 },
                    { name: "LSTM-Attn", weight: 14 },
                    { name: "XGBoost", weight: 16 },
                  ].map((item, index) => (
                    <div key={item.name} className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-[var(--nq-text-secondary)]">{item.name}</span>
                        <span className="font-medium text-[var(--nq-text-primary)]">{item.weight}%</span>
                      </div>
                      <div className="h-2 rounded-full bg-white/[0.08]">
                        <div className="h-2 rounded-full bg-[linear-gradient(90deg,var(--nq-accent),#69f5ff)]" style={{ width: `${item.weight}%`, opacity: 0.84 - index * 0.08 }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div>
                <CardTitle>Recent activity</CardTitle>
                <CardDescription>Important live events from model, market, and execution layers.</CardDescription>
              </div>
              <Badge variant="outline" className="border-white/10 bg-white/[0.06] text-[10px] uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">
                4 updates
              </Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              {activityFeed.map((item, idx) => {
                const Icon = item.icon;

                return (
                  <motion.div
                    key={item.id}
                    initial={{ opacity: 0, x: 12 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.12 + idx * 0.05, duration: 0.3 }}
                    whileHover={{ y: -2 }}
                    className="rounded-[1.25rem] border border-white/10 bg-white/5 p-4 transition hover:bg-white/[0.08]"
                  >
                    <div className="flex items-start gap-3">
                      <div className="rounded-2xl border border-white/10 bg-[linear-gradient(135deg,rgba(0,212,245,0.16),rgba(255,255,255,0.05))] p-2.5 text-[var(--nq-accent)]">
                        <Icon className="h-4.5 w-4.5" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-start justify-between gap-3">
                          <p className="font-medium text-[var(--nq-text-primary)]">{item.title}</p>
                          <span className="shrink-0 text-xs text-[var(--nq-text-muted)]">{item.time}</span>
                        </div>
                        <p className="mt-1 text-sm leading-6 text-[var(--nq-text-secondary)]">{item.description}</p>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </CardContent>
            <CardFooter>
              <Button variant="ghost" leftIcon={<ArrowRight className="h-4 w-4" />}>
                View all activity
              </Button>
              <Badge variant="secondary">Synced 30s ago</Badge>
            </CardFooter>
          </Card>
        </motion.div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, delay: 0.18 }}>
          <Card>
            <CardHeader>
              <div>
                <CardTitle>Open positions</CardTitle>
                <CardDescription>Readable portfolio table with strong spacing, contrast, and room for expansion.</CardDescription>
              </div>
              <Button variant="secondary" size="sm" leftIcon={<Download className="h-4 w-4" />}>
                Export CSV
              </Button>
            </CardHeader>
            <CardContent className="overflow-hidden">
              <div className="overflow-x-auto rounded-[1.25rem] border border-white/10 bg-white/[0.04] p-2">
                <Table>
                  <thead>
                    <TableRow>
                      <TableHead>Symbol</TableHead>
                      <TableHead>Side</TableHead>
                      <TableHead>Quantity</TableHead>
                      <TableHead>P&amp;L</TableHead>
                      <TableHead>Exposure</TableHead>
                    </TableRow>
                  </thead>
                  <tbody>
                    {openPositions.map((row) => (
                      <TableRow key={row.symbol}>
                        <TableCell className="font-semibold">{row.symbol}</TableCell>
                        <TableCell>{row.side}</TableCell>
                        <TableCell>{row.quantity}</TableCell>
                        <TableCell className={row.pnl.startsWith("-") ? "text-[var(--nq-bear)]" : "text-[var(--nq-bull)]"}>{row.pnl}</TableCell>
                        <TableCell>{row.exposure}</TableCell>
                      </TableRow>
                    ))}
                  </tbody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, delay: 0.22 }} className="space-y-6">
          <Card>
            <CardHeader>
              <div>
                <CardTitle>Quick actions</CardTitle>
                <CardDescription>High-value actions that feel like a real operations cockpit.</CardDescription>
              </div>
              <Badge variant="outline" className="border-white/10 bg-white/[0.06] text-[10px] uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">
                Focus mode
              </Badge>
            </CardHeader>
            <CardContent className="grid gap-3">
              {quickActions.map((action) => {
                const Icon = action.icon;

                return (
                  <button key={action.title} type="button" className="group flex items-start gap-3 rounded-[1.25rem] border border-white/10 bg-white/5 p-4 text-left transition hover:-translate-y-0.5 hover:bg-white/[0.08]">
                    <div className="rounded-2xl border border-white/10 bg-[linear-gradient(135deg,rgba(255,255,255,0.12),rgba(255,255,255,0.04))] p-2.5 text-[var(--nq-text-primary)] transition group-hover:text-[var(--nq-accent)]">
                      <Icon className="h-4.5 w-4.5" />
                    </div>
                    <div>
                      <p className="font-medium text-[var(--nq-text-primary)]">{action.title}</p>
                      <p className="mt-1 text-sm leading-6 text-[var(--nq-text-secondary)]">{action.description}</p>
                    </div>
                  </button>
                );
              })}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div>
                <CardTitle>Market news</CardTitle>
                <CardDescription>Scrollable sentiment feed aligned with the prompt’s live news rail.</CardDescription>
              </div>
              <Badge variant="bull">FinBERT scored</Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              {newsFeed.map((item) => (
                <div key={item.headline} className="flex items-start gap-3 rounded-[1.1rem] border border-white/10 bg-white/5 p-4">
                  <span className={`mt-1 h-2.5 w-2.5 rounded-full ${item.tone === "bull" ? "bg-[var(--nq-bull)]" : "bg-[var(--nq-warning)]"}`} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">{item.source}</p>
                      <Badge variant={item.tone === "bull" ? "bull" : "secondary"} className="px-2 py-0.5 text-[10px] uppercase tracking-[0.12em]">
                        {item.tone === "bull" ? "Positive" : "Neutral"}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm leading-6 text-[var(--nq-text-primary)]">{item.headline}</p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div>
                <CardTitle>Workspace checklist</CardTitle>
                <CardDescription>Quick confirmation that the UI is ready for local validation.</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                "Premium gradients and layered depth",
                "Readable type hierarchy and clear contrast",
                "Responsive stacking for smaller viewports",
                "Charts, tables, actions, and alerts are cohesive",
              ].map((item) => (
                <div key={item} className="flex items-center gap-3 rounded-[1.15rem] border border-white/10 bg-white/5 px-4 py-3">
                  <ShieldCheck className="h-4.5 w-4.5 text-[var(--nq-bull)]" />
                  <span className="text-sm text-[var(--nq-text-secondary)]">{item}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </motion.div>
      </section>

      <Modal open={createAlertOpen} onOpenChange={setCreateAlertOpen} title="Create alert" description="Set a premium signal rule for the current market setup.">
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Input defaultValue="AAPL" />
            <Input defaultValue="Breakout > 1.8%" />
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <Input defaultValue="Trigger once" />
            <Input defaultValue="Notify desk + email" />
          </div>

          <div className="flex flex-wrap items-center justify-end gap-2 pt-2">
            <Button variant="ghost" type="button" onClick={() => setCreateAlertOpen(false)}>
              Cancel
            </Button>
            <Button type="button">Create rule</Button>
          </div>
        </div>
      </Modal>
    </motion.div>
  );
}