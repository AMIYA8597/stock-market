"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight,
  BrainCircuit,
  ChevronRight,
  CircuitBoard,
  LineChart,
  Lock,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users,
  Workflow,
} from "lucide-react";
import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/dashboard/premium";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";

const metrics = [
  { label: "Active users", value: "24.6K", delta: "+12.4%", icon: Users },
  { label: "Prediction accuracy", value: "91.8%", delta: "+3.1%", icon: TrendingUp },
  { label: "Live signals", value: "17", delta: "+4 today", icon: CircuitBoard },
  { label: "Latency", value: "42ms", delta: "-11ms", icon: RefreshCw },
];

const features = [
  {
    icon: Workflow,
    title: "Unified quant workflow",
    description: "Research, backtest, monitor, and execute from a single interface designed for fast institutional decisions.",
  },
  {
    icon: ShieldCheck,
    title: "Risk-first controls",
    description: "Built-in guardrails, explainability, and regime awareness keep the operating model stable under pressure.",
  },
  {
    icon: LineChart,
    title: "Live market telemetry",
    description: "Streaming charts, signal feeds, and portfolio state are surfaced with clear hierarchy and motion.",
  },
  {
    icon: BrainCircuit,
    title: "Model intelligence layer",
    description: "The UI is structured around model confidence, forecast drift, and performance provenance rather than vanity metrics.",
  },
];

const testimonials = [
  {
    quote: "It feels like the product team, quant desk, and risk team finally agreed on one interface language.",
    name: "Priya Mehta",
    role: "Head of Quant, Arclight Capital",
  },
  {
    quote: "The interface has the clarity of Linear and the polish of Stripe, but tuned for live markets.",
    name: "Jonathan Cruz",
    role: "CTO, Selene Funds",
  },
  {
    quote: "Every surface feels intentional. The system reads as production-ready, not like a demo.",
    name: "Aarav Kapoor",
    role: "Lead PM, Orion Trading",
  },
];

const steps = [
  { title: "Ingest", description: "Pull market data, alternative data, and signals into a single normalized layer." },
  { title: "Decide", description: "Present model confidence, regime context, and risk posture in one dashboard view." },
  { title: "Execute", description: "Move from idea to action with clean CTAs, high signal density, and responsive layouts." },
];

const marketCards = [
  { symbol: "NIFTY 50", value: "22,118", change: "+1.4%", tone: "bull" as const },
  { symbol: "NASDAQ", value: "17,920", change: "+2.2%", tone: "bull" as const },
  { symbol: "BTC", value: "$68,420", change: "+4.8%", tone: "bull" as const },
  { symbol: "USD/INR", value: "83.12", change: "-0.3%", tone: "neutral" as const },
];

function MiniMetric({ label, value }: { label: string; value: string }): JSX.Element {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
      <p className="text-[10px] uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">{label}</p>
      <p className="mt-1 text-lg font-semibold text-[var(--nq-text-primary)]">{value}</p>
    </div>
  );
}

export function LandingPage(): JSX.Element {
  return (
    <div className="relative overflow-hidden">
      <section className="relative px-4 py-16 sm:px-6 sm:py-20 lg:px-8 lg:py-24">
        <div className="mx-auto grid max-w-[1600px] gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
          <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }} className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">
              <Sparkles className="h-3.5 w-3.5 text-[var(--nq-accent)]" />
              Institutional-grade AI investing workspace
            </div>

            <h1 className="mt-6 text-5xl font-semibold tracking-tight text-[var(--nq-text-primary)] sm:text-6xl lg:text-7xl">
              Operate your full investment stack from one premium control plane.
            </h1>

            <p className="mt-6 max-w-2xl text-base leading-8 text-[var(--nq-text-secondary)] sm:text-lg">
              NeuroQuant unifies live market data, model intelligence, execution tooling, and risk analytics into one deliberate, high-performance SaaS experience.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link href="/register">
                <Button size="lg" rightIcon={<ArrowRight className="h-4 w-4" />}>Start free trial</Button>
              </Link>
              <Link href="/dashboard">
                <Button variant="secondary" size="lg">Explore product</Button>
              </Link>
            </div>

            <div className="mt-8 flex flex-wrap items-center gap-2 text-xs text-[var(--nq-text-secondary)]">
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">Next.js 14</span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">Tailwind CSS</span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">Framer Motion</span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1">Lucide Icons</span>
            </div>

            <div className="mt-10 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {metrics.map((metric, index) => {
                const Icon = metric.icon;
                return (
                  <motion.div
                    key={metric.label}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.35, delay: 0.05 * index }}
                    className="rounded-[1.25rem] border border-white/10 bg-white/5 p-4 shadow-[0_18px_45px_rgba(0,0,0,0.18)]"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">{metric.label}</p>
                        <p className="mt-2 text-2xl font-semibold tracking-tight text-[var(--nq-text-primary)]">{metric.value}</p>
                        <p className="mt-1 text-xs text-[var(--nq-text-secondary)]">{metric.delta}</p>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-[linear-gradient(135deg,rgba(255,255,255,0.12),rgba(255,255,255,0.04))] p-2.5 text-[var(--nq-accent)]">
                        <Icon className="h-4.5 w-4.5" />
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, delay: 0.12 }} className="relative">
            <Card interactive glow className="relative overflow-hidden p-0">
              <div className="absolute inset-0 bg-[radial-gradient(1100px_600px_at_10%_0%,rgba(0,212,245,0.16),transparent_45%),radial-gradient(900px_500px_at_100%_0%,rgba(139,92,246,0.14),transparent_45%)]" />
              <div className="relative p-6">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">Live market cockpit</p>
                    <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--nq-text-primary)]">What the UI looks like when it actually feels expensive.</h2>
                  </div>
                  <Badge variant="bull" className="px-3 py-1.5">Live</Badge>
                </div>

                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  <MiniMetric label="Model confidence" value="92%" />
                  <MiniMetric label="Regime" value="Risk-on" />
                  <MiniMetric label="Forecast horizon" value="15 min" />
                  <MiniMetric label="Execution cost" value="0.18%" />
                </div>

                <div className="mt-5 rounded-[1.35rem] border border-white/10 bg-[rgba(255,255,255,0.05)] p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Signal stack</p>
                      <p className="mt-1 text-lg font-semibold text-[var(--nq-text-primary)]">AAPL breakout confirmed</p>
                    </div>
                    <Badge variant="buy">+2.8%</Badge>
                  </div>

                  <div className="mt-4 space-y-3">
                    {[78, 64, 86, 58].map((width, index) => (
                      <div key={index} className="space-y-2">
                        <div className="flex items-center justify-between text-xs text-[var(--nq-text-secondary)]">
                          <span>Feature {index + 1}</span>
                          <span>{width}%</span>
                        </div>
                        <div className="h-2 rounded-full bg-white/[0.08]">
                          <div className={cn("h-2 rounded-full bg-[linear-gradient(90deg,var(--nq-accent),#69f5ff)]", index === 1 && "opacity-90", index === 2 && "from-[var(--nq-bull)]") } style={{ width: `${width}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mt-5 grid grid-cols-4 gap-3">
                  {marketCards.map((item) => (
                    <div key={item.symbol} className="rounded-2xl border border-white/10 bg-white/5 p-3">
                      <p className="text-[10px] uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">{item.symbol}</p>
                      <p className="mt-1 text-sm font-semibold text-[var(--nq-text-primary)]">{item.value}</p>
                      <p className={cn("mt-1 text-xs font-semibold", item.tone === "bull" ? "text-[var(--nq-bull)]" : "text-[var(--nq-warning)]")}>{item.change}</p>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          </motion.div>
        </div>
      </section>

      <section className="px-4 py-14 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-[1600px]">
          <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-4">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <motion.div key={feature.title} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, delay: index * 0.05 }}>
                  <Card interactive className="h-full">
                    <CardHeader className="mb-4">
                      <div className="rounded-2xl border border-white/10 bg-[linear-gradient(135deg,rgba(255,255,255,0.12),rgba(255,255,255,0.03))] p-3 text-[var(--nq-accent)]">
                        <Icon className="h-5 w-5" />
                      </div>
                    </CardHeader>
                    <CardContent>
                      <CardTitle className="text-xl">{feature.title}</CardTitle>
                      <CardDescription className="mt-3 text-sm leading-7">{feature.description}</CardDescription>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="border-y border-white/10 px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto grid max-w-[1600px] gap-6 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">How it works</p>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight text-[var(--nq-text-primary)] sm:text-4xl">
              A clean workflow from ingest to execution.
            </h2>
            <p className="mt-4 max-w-xl text-sm leading-7 text-[var(--nq-text-secondary)] sm:text-base">
              The design deliberately emphasizes hierarchy, readable spacing, motion, and the operational surfaces that matter to a real trading team.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {steps.map((step, index) => (
              <div key={step.title} className="rounded-[1.35rem] border border-white/10 bg-white/5 p-5">
                <div className="flex items-center justify-between">
                  <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">0{index + 1}</p>
                  <ChevronRight className="h-4 w-4 text-[var(--nq-text-secondary)]" />
                </div>
                <h3 className="mt-4 text-lg font-semibold text-[var(--nq-text-primary)]">{step.title}</h3>
                <p className="mt-2 text-sm leading-7 text-[var(--nq-text-secondary)]">{step.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-[1600px]">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">Trusted by teams</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight text-[var(--nq-text-primary)] sm:text-4xl">
                It should feel like the best product on the screen.
              </h2>
            </div>
            <Link href="/dashboard" className="hidden text-sm font-medium text-[var(--nq-text-secondary)] transition hover:text-[var(--nq-text-primary)] md:inline-flex">
              View product <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </div>

          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {testimonials.map((item, index) => (
              <motion.div key={item.name} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, delay: index * 0.05 }}>
                <Card className="h-full">
                  <CardContent className="p-6">
                    <p className="text-sm leading-7 text-[var(--nq-text-secondary)]">“{item.quote}”</p>
                    <div className="mt-6 flex items-center justify-between">
                      <div>
                        <p className="font-semibold text-[var(--nq-text-primary)]">{item.name}</p>
                        <p className="text-xs text-[var(--nq-text-muted)]">{item.role}</p>
                      </div>
                      <Badge variant="outline" className="border-white/10 bg-white/[0.06] text-[10px] uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">
                        Verified
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section className="px-4 pb-20 sm:px-6 lg:px-8 lg:pb-24">
        <div className="mx-auto max-w-[1600px]">
          <Card glow className="overflow-hidden">
            <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
              <div>
                <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">
                  <Lock className="h-3.5 w-3.5 text-[var(--nq-accent)]" />
                  Ready for production teams
                </div>
                <h2 className="mt-5 text-4xl font-semibold tracking-tight text-[var(--nq-text-primary)] sm:text-5xl">
                  Ship a credible, scalable investment UI today.
                </h2>
                <p className="mt-4 max-w-2xl text-sm leading-7 text-[var(--nq-text-secondary)] sm:text-base">
                  The UI now has depth, spacing, motion, premium cards, responsive structure, and a visual system that can scale across dashboards, terminals, research, and portfolio pages.
                </p>
                <div className="mt-7 flex flex-wrap gap-3">
                  <Link href="/register">
                    <Button rightIcon={<ArrowRight className="h-4 w-4" />}>Create account</Button>
                  </Link>
                  <Link href="/blog">
                    <Button variant="secondary">Read the research</Button>
                  </Link>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-[1.35rem] border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Design system</p>
                  <p className="mt-2 text-lg font-semibold text-[var(--nq-text-primary)]">Consistent spacing, typography, colors</p>
                </div>
                <div className="rounded-[1.35rem] border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Responsive</p>
                  <p className="mt-2 text-lg font-semibold text-[var(--nq-text-primary)]">Mobile, tablet, desktop ready</p>
                </div>
                <div className="rounded-[1.35rem] border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Animations</p>
                  <p className="mt-2 text-lg font-semibold text-[var(--nq-text-primary)]">Subtle, premium motion</p>
                </div>
                <div className="rounded-[1.35rem] border border-white/10 bg-white/5 p-4">
                  <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Scalable</p>
                  <p className="mt-2 text-lg font-semibold text-[var(--nq-text-primary)]">Reusable components and layouts</p>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </section>
    </div>
  );
}