"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader, CardTitle } from "@/components/dashboard/premium";
import {
  contractsApi,
  type BacktestRunRequest,
  type BacktestRunResponse,
  type BacktestStatusResponse,
} from "@/lib/contracts-api";
import { ChartCard, SimpleLineAreaChart, type LineAreaPoint } from "@/components/charts";
import { safeFormat } from "@/lib/formatters";

const DEFAULT_SYMBOLS = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"];
const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
const cleanWsUrl = WS_URL.endsWith("/ws") ? WS_URL.slice(0, -3) : WS_URL;

function toPercent(value: unknown): string {
  if (value === null || value === undefined) {
    return "--";
  }
  const num = Number(value);
  if (Number.isNaN(num)) {
    return "--";
  }
  return `${(num * 100).toFixed(2)}%`;
}

export default function BacktestLabPage(): JSX.Element {
  const [strategyName, setStrategyName] = useState<BacktestRunRequest["strategy_name"]>("ml_alpha");
  const [symbolsInput, setSymbolsInput] = useState<string>(DEFAULT_SYMBOLS.join(","));
  const [startDate, setStartDate] = useState<string>("2018-01-01");
  const [endDate, setEndDate] = useState<string>("2024-12-31");
  const [benchmark, setBenchmark] = useState<string>("^NSEI");
  const [initialCapital, setInitialCapital] = useState<number>(1_000_000);
  const [commissionPct, setCommissionPct] = useState<number>(0.001);
  const [slippagePct, setSlippagePct] = useState<number>(0.0005);

  const [job, setJob] = useState<BacktestRunResponse | null>(null);
  const [status, setStatus] = useState<BacktestStatusResponse | null>(null);
  const [running, setRunning] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [wsStatus, setWsStatus] = useState<"connected" | "reconnecting" | "disconnected">("disconnected");
  const [error, setError] = useState<string | null>(null);
  const [progressHistory, setProgressHistory] = useState<LineAreaPoint[]>([]);

  const symbols = useMemo(
    () =>
      symbolsInput
        .split(",")
        .map((item) => item.trim().toUpperCase())
        .filter((item) => item.length > 0),
    [symbolsInput],
  );

  useEffect(() => {
    let mounted = true;

    async function preloadUniverse(): Promise<void> {
      try {
        const movers = await contractsApi.getMovers("NSE", "momentum");
        if (!mounted || movers.length === 0) {
          return;
        }
        const dynamicSymbols = movers.slice(0, 8).map((item) => item.ticker.toUpperCase());
        setSymbolsInput(dynamicSymbols.join(","));
      } catch {
        // Keep current universe input if contract fetch fails.
      }
    }

    void preloadUniverse();

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!job?.job_id || !running) {
      return;
    }

    let active = true;
    let ws: WebSocket | null = null;

    try {
      setWsStatus("reconnecting");
      ws = new WebSocket(`${cleanWsUrl}/ws/backtest-progress`);

      ws.onopen = () => {
        setWsStatus("connected");
      };

      ws.onmessage = (event) => {
        if (!active) {
          return;
        }

        try {
          const payload = JSON.parse(event.data as string) as {
            type?: string;
            job_id?: string;
            pct?: number;
          };

          if (payload.type !== "progress" || payload.job_id !== job.job_id || typeof payload.pct !== "number") {
            return;
          }

          const nextProgress = payload.pct;

          setStatus((prev) => ({
            job_id: job.job_id,
            status: prev?.status ?? "RUNNING",
            progress_pct: Math.max(0, Math.min(100, nextProgress)),
            result_preview: prev?.result_preview,
          }));
          setProgressHistory((prev) => {
            const next = [...prev, { label: String(prev.length + 1), value: Math.max(0, Math.min(100, nextProgress)) }];
            return next.slice(-80);
          });
        } catch {
          // Ignore malformed payloads.
        }
      };

      ws.onclose = () => {
        setWsStatus("reconnecting");
      };

      ws.onerror = () => {
        if (ws) {
          ws.close();
        }
      };
    } catch {
      setWsStatus("disconnected");
    }

    const timer = setInterval(() => {
      void (async () => {
        try {
          const nextStatus = await contractsApi.getBacktestStatus(job.job_id);
          if (!active) {
            return;
          }
          setStatus(nextStatus);
          if (typeof nextStatus.progress_pct === "number") {
            const nextProgress = nextStatus.progress_pct;
            setProgressHistory((prev) => {
              const lastValue = prev.at(-1)?.value ?? null;
              if (lastValue === nextProgress) {
                return prev;
              }
              const next = [...prev, { label: String(prev.length + 1), value: nextProgress }];
              return next.slice(-80);
            });
          }
          if (nextStatus.status === "COMPLETED" || nextStatus.status === "FAILED") {
            setRunning(false);
          }
        } catch (requestError) {
          if (!active) {
            return;
          }
          const message = requestError instanceof Error ? requestError.message : "Unable to fetch backtest status.";
          setError(message);
          setRunning(false);
        }
      })();
    }, 3000);

    return () => {
      active = false;
      clearInterval(timer);
      setWsStatus("disconnected");
      if (ws) {
        ws.close();
      }
    };
  }, [job?.job_id, running]);

  async function onRunBacktest(): Promise<void> {
    if (symbols.length === 0) {
      setError("Provide at least one symbol.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const payload: BacktestRunRequest = {
        strategy_name: strategyName,
        symbols,
        start_date: startDate,
        end_date: endDate,
        benchmark,
        initial_capital: initialCapital,
        commission_pct: commissionPct,
        slippage_pct: slippagePct,
      };

      const runResponse = await contractsApi.runBacktest(payload);
      setJob(runResponse);
      setStatus({ job_id: runResponse.job_id, status: runResponse.status, progress_pct: 0 });
      setProgressHistory([{ label: "1", value: 0 }]);
      setRunning(true);
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Unable to submit backtest.";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(1000px_500px_at_0%_0%,rgba(0,212,245,0.12),transparent_45%),radial-gradient(900px_420px_at_100%_0%,rgba(139,92,246,0.10),transparent_45%),var(--nq-bg-base)] p-4 text-[var(--nq-text-primary)] sm:p-6">
      <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} className="mb-6 grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <Card glow className="relative overflow-hidden px-6 py-6 sm:px-8">
          <div className="absolute inset-0 bg-[radial-gradient(1000px_420px_at_0%_0%,rgba(0,212,245,0.16),transparent_45%),radial-gradient(800px_360px_at_100%_0%,rgba(139,92,246,0.14),transparent_45%)]" />
          <div className="relative space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="bull" className="px-3 py-1.5 text-[10px] uppercase tracking-[0.16em]">Backtest lab</Badge>
              <Badge variant="outline" className="px-3 py-1.5 text-[10px] uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">Walk-forward + Monte Carlo</Badge>
            </div>
            <div className="max-w-3xl space-y-3">
              <h1 className="text-4xl font-semibold tracking-tight text-[var(--nq-text-primary)] sm:text-5xl">Research-grade strategy testing with clean, readable results.</h1>
              <p className="max-w-2xl text-sm leading-7 text-[var(--nq-text-secondary)] sm:text-base">
                Configure a strategy, run it against a market universe, and inspect the complete result stack with performance, progress, and distribution views.
              </p>
            </div>
          </div>
        </Card>

        <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
          {[
            ["Universe", `${symbols.length} symbols`],
            ["Capital", initialCapital.toLocaleString("en-IN")],
            ["Feed", running ? `Live ${wsStatus}` : "Idle"],
          ].map(([label, value]) => (
            <Card key={label} className="p-4">
              <CardHeader className="mb-3">
                <CardTitle className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">{label}</CardTitle>
              </CardHeader>
              <div className="text-lg font-semibold text-[var(--nq-text-primary)]">{value}</div>
            </Card>
          ))}
        </div>
      </motion.section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[2fr_3fr]">
        <section className="rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-5 shadow-[0_18px_48px_rgba(0,0,0,0.22)]">
          <h2 className="mb-4 text-sm font-medium uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Strategy Configurator</h2>
          <div className="space-y-4 text-sm">
            <label className="block">
              <span className="mb-1 block text-xs text-[var(--nq-text-secondary)]">Strategy</span>
              <select
                value={strategyName}
                onChange={(event) => setStrategyName(event.target.value as BacktestRunRequest["strategy_name"])}
                className="w-full rounded-[1rem] border border-white/10 bg-[var(--nq-bg-base)] px-3 py-2 text-sm text-[var(--nq-text-primary)] outline-none transition focus:border-[var(--nq-accent)]"
              >
                <option value="ml_alpha">ml_alpha</option>
                <option value="momentum">momentum</option>
                <option value="mean_reversion">mean_reversion</option>
                <option value="volatility_breakout">volatility_breakout</option>
                <option value="stat_arb">stat_arb</option>
              </select>
            </label>

            <label className="block">
              <span className="mb-1 block text-xs text-[var(--nq-text-secondary)]">Universe (comma separated)</span>
              <textarea
                className="h-20 w-full rounded-[1rem] border border-white/10 bg-[var(--nq-bg-base)] px-3 py-2 text-sm text-[var(--nq-text-primary)] outline-none transition focus:border-[var(--nq-accent)]"
                value={symbolsInput}
                onChange={(event) => setSymbolsInput(event.target.value)}
              />
            </label>

            <div className="grid gap-3 sm:grid-cols-2">
              <label>
                <span className="mb-1 block text-xs text-[var(--nq-text-secondary)]">Date From</span>
                <input
                  type="date"
                  value={startDate}
                  onChange={(event) => setStartDate(event.target.value)}
                  className="w-full rounded-[1rem] border border-white/10 bg-[var(--nq-bg-base)] px-3 py-2 text-[var(--nq-text-primary)] outline-none transition focus:border-[var(--nq-accent)]"
                />
              </label>
              <label>
                <span className="mb-1 block text-xs text-[var(--nq-text-secondary)]">Date To</span>
                <input
                  type="date"
                  value={endDate}
                  onChange={(event) => setEndDate(event.target.value)}
                  className="w-full rounded-[1rem] border border-white/10 bg-[var(--nq-bg-base)] px-3 py-2 text-[var(--nq-text-primary)] outline-none transition focus:border-[var(--nq-accent)]"
                />
              </label>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <label>
                <span className="mb-1 block text-xs text-[var(--nq-text-secondary)]">Initial Capital</span>
                <input
                  type="number"
                  value={initialCapital}
                  onChange={(event) => setInitialCapital(Number(event.target.value) || 0)}
                  className="w-full rounded-[1rem] border border-white/10 bg-[var(--nq-bg-base)] px-3 py-2 text-[var(--nq-text-primary)] outline-none transition focus:border-[var(--nq-accent)]"
                />
              </label>
              <label>
                <span className="mb-1 block text-xs text-[var(--nq-text-secondary)]">Commission % (fraction)</span>
                <input
                  type="number"
                  step="0.0001"
                  value={commissionPct}
                  onChange={(event) => setCommissionPct(Number(event.target.value) || 0)}
                  className="w-full rounded-[1rem] border border-white/10 bg-[var(--nq-bg-base)] px-3 py-2 text-[var(--nq-text-primary)] outline-none transition focus:border-[var(--nq-accent)]"
                />
              </label>
              <label>
                <span className="mb-1 block text-xs text-[var(--nq-text-secondary)]">Slippage % (fraction)</span>
                <input
                  type="number"
                  step="0.0001"
                  value={slippagePct}
                  onChange={(event) => setSlippagePct(Number(event.target.value) || 0)}
                  className="w-full rounded-[1rem] border border-white/10 bg-[var(--nq-bg-base)] px-3 py-2 text-[var(--nq-text-primary)] outline-none transition focus:border-[var(--nq-accent)]"
                />
              </label>
            </div>

            <label className="block">
              <span className="mb-1 block text-xs text-[var(--nq-text-secondary)]">Benchmark</span>
              <input
                type="text"
                value={benchmark}
                onChange={(event) => setBenchmark(event.target.value)}
                className="w-full rounded-[1rem] border border-white/10 bg-[var(--nq-bg-base)] px-3 py-2 text-[var(--nq-text-primary)] outline-none transition focus:border-[var(--nq-accent)]"
              />
            </label>

            <button
              onClick={() => void onRunBacktest()}
              disabled={submitting}
              className="w-full rounded-[1rem] bg-[linear-gradient(135deg,var(--nq-accent),#69f5ff)] px-4 py-2 text-sm font-semibold text-[#07111A] shadow-[0_14px_28px_rgba(0,212,245,0.28)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting ? "Submitting..." : "Run Backtest"}
            </button>
            {error ? <p className="text-xs text-[var(--nq-accent-red)]">{error}</p> : null}
          </div>
        </section>

        <section className="space-y-4">
          <ChartCard title="Job Status" subtitle="WebSocket stream with polling fallback">
            {!job ? <p className="text-sm text-[var(--nq-text-secondary)]">Submit a strategy run to generate a backtest job.</p> : null}
            {job ? (
              <div className="space-y-3 text-sm">
                <div className="grid gap-2 sm:grid-cols-3">
                  <div className="rounded-[1rem] border border-white/10 bg-white/[0.04] px-3 py-2">
                    <p className="text-[11px] text-[var(--nq-text-secondary)]">Job ID</p>
                    <p className="mt-1 font-medium">{job.job_id}</p>
                  </div>
                  <div className="rounded-[1rem] border border-white/10 bg-white/[0.04] px-3 py-2">
                    <p className="text-[11px] text-[var(--nq-text-secondary)]">Status</p>
                    <p className="mt-1 font-medium">{status?.status ?? job.status}</p>
                  </div>
                  <div className="rounded-[1rem] border border-white/10 bg-white/[0.04] px-3 py-2">
                    <p className="text-[11px] text-[var(--nq-text-secondary)]">Progress</p>
                    <p className="mt-1 font-medium">{typeof status?.progress_pct === "number" ? `${status.progress_pct}%` : "--"}</p>
                  </div>
                </div>

                <div className="rounded-[1rem] border border-white/10 bg-white/[0.04] px-3 py-2 text-xs">
                  <p className="text-[var(--nq-text-secondary)]">Preview Sharpe: {safeFormat(status?.result_preview?.sharpe, 3)}</p>
                  <p className="text-[var(--nq-text-secondary)]">Preview Max Drawdown: {toPercent(status?.result_preview?.max_drawdown)}</p>
                </div>

                <div className="h-[140px] rounded-[1rem] border border-white/10 bg-[rgba(255,255,255,0.03)] p-2">
                  <SimpleLineAreaChart
                    data={progressHistory.length > 0 ? progressHistory : [{ label: "1", value: 0 }]}
                    mode="line"
                    stroke="var(--nq-accent-cyan)"
                    yTickFormatter={(value) => `${safeFormat(value, 0)}%`}
                  />
                </div>

                <div className="flex items-center gap-3">
                  <Link
                    href={`/backtest-lab/results/${encodeURIComponent(job.job_id)}`}
                    className="rounded-[1rem] border border-white/10 bg-white/[0.04] px-3 py-2 text-xs transition-colors hover:border-[var(--nq-accent)]"
                  >
                    Open Results
                  </Link>
                  {running ? <span className="text-xs text-[var(--nq-text-secondary)]">Progress feed: {wsStatus} + poll fallback 3s</span> : null}
                </div>
              </div>
            ) : null}
          </ChartCard>

          <div className="rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-4">
            <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Current Run Snapshot</h2>
            <div className="grid gap-2 text-xs sm:grid-cols-2">
              {[
                ["Strategy", strategyName],
                ["Universe Size", String(symbols.length)],
                ["Benchmark", benchmark],
                ["Capital", initialCapital.toLocaleString("en-IN")],
              ].map(([label, value]) => (
                <div key={label} className="rounded-[1rem] border border-white/10 bg-white/[0.04] px-3 py-2">
                  <p className="text-[11px] text-[var(--nq-text-secondary)]">{label}</p>
                  <p className="mt-1 text-sm font-medium">{value}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
