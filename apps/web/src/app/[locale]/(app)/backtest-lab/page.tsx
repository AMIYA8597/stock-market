"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "@/i18n/navigation";
import { contractsApi } from "@/lib/contracts-api";
import { Button, Input } from "@neuroquant/ui";
import { AuthGuard } from "@/components/auth/AuthGuard";

const STRATEGY_OPTIONS = [
  { value: "ensemble", label: "Ensemble (platform AI signals)" },
  { value: "ma_crossover", label: "MA Crossover" },
  { value: "rsi_mrv", label: "RSI Mean Reversion" },
];

function todayISO(): string {
  return new Date().toISOString().split("T")[0] as string;
}

function yearAgoISO(): string {
  return new Date(Date.now() - 365 * 24 * 60 * 60 * 1000)
    .toISOString()
    .split("T")[0] as string;
}

export default function BacktestLabRoutePage(): JSX.Element {
  return (
    <AuthGuard>
      <BacktestLabPage />
    </AuthGuard>
  );
}

function BacktestLabPage(): JSX.Element {
  const router = useRouter();
  const [strategyName, setStrategyName] = useState<string>("ensemble");
  const [symbol, setSymbol] = useState<string>("RELIANCE.NS");
  const [startDate, setStartDate] = useState<string>(yearAgoISO());
  const [endDate, setEndDate] = useState<string>(todayISO());
  const [initialCapital, setInitialCapital] = useState<string>("1000000");
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [statusText, setStatusText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollTimer.current) {
      clearTimeout(pollTimer.current);
      pollTimer.current = null;
    }
  }, []);

  const pollStatus = useCallback(
    (jobId: string) => {
      contractsApi
        .getBacktestStatus(jobId)
        .then((status) => {
          if (status.status === "DONE" || status.status === "COMPLETED" || status.status === "SUCCESS") {
            setStatusText("Done. Loading results...");
            router.push(`/backtest-lab/results/${jobId}`);
            return;
          }
          if (status.status === "FAILED") {
            setSubmitting(false);
            setError(status.error_message || "Backtest job failed.");
            return;
          }
          setStatusText(
            `${status.status}${
              typeof status.progress_pct === "number" ? ` — ${status.progress_pct}%` : ""
            }`,
          );
          pollTimer.current = setTimeout(() => pollStatus(jobId), 2500);
        })
        .catch((pollError) => {
          setSubmitting(false);
          setError(
            pollError instanceof Error ? pollError.message : "Failed to check job status.",
          );
        });
    },
    [router],
  );

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      stopPolling();
      setError(null);
      setSubmitting(true);
      setStatusText("Submitting job...");

      const capital = Number(initialCapital);
      if (!symbol.trim()) {
        setSubmitting(false);
        setError("Enter a symbol to backtest.");
        return;
      }
      if (!Number.isFinite(capital) || capital <= 0) {
        setSubmitting(false);
        setError("Initial capital must be a positive number.");
        return;
      }

      try {
        const run = await contractsApi.runBacktest({
          strategy_name: strategyName,
          symbol: symbol.trim().toUpperCase(),
          start_date: startDate,
          end_date: endDate,
          initial_capital: capital,
        });
        setStatusText(`Job ${run.job_id} — ${run.status}`);
        pollStatus(run.job_id);
      } catch (submitError) {
        setSubmitting(false);
        setError(
          submitError instanceof Error ? submitError.message : "Failed to start backtest job.",
        );
      }
    },
    [strategyName, symbol, startDate, endDate, initialCapital, pollStatus, stopPolling],
  );

  return (
    <main className="min-h-screen bg-[radial-gradient(1000px_500px_at_0%_0%,rgba(0,212,245,0.12),transparent_45%),radial-gradient(900px_420px_at_100%_0%,rgba(139,92,246,0.10),transparent_45%),var(--nq-bg-base)] p-4 text-[var(--nq-text-primary)] sm:p-6 lg:p-8">
      <section className="mb-6 rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-5 shadow-[0_18px_48px_rgba(0,0,0,0.22)]">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Backtest Lab</h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--nq-text-secondary)]">
          Runs a single-symbol, event-driven backtest against the platform&apos;s stored
          ensemble AI signals for the chosen date range. The strategy label is stored with
          the job for your own reference — the engine currently always replays the same
          stored signals, it does not yet dispatch to different strategy logic per label.
        </p>
      </section>

      <section className="rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-5">
        <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <label className="flex flex-col gap-1.5 text-xs">
            <span className="uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">
              Symbol
            </span>
            <Input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              placeholder="RELIANCE.NS"
              disabled={submitting}
            />
          </label>

          <label className="flex flex-col gap-1.5 text-xs">
            <span className="uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">
              Strategy label
            </span>
            <select
              value={strategyName}
              onChange={(e) => setStrategyName(e.target.value)}
              disabled={submitting}
              className="h-10 rounded-[var(--ds-radius-lg,0.5rem)] border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 text-sm text-[var(--nq-text-primary)]"
            >
              {STRATEGY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1.5 text-xs">
            <span className="uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">
              Initial Capital (INR)
            </span>
            <Input
              type="number"
              min={1000}
              step={1}
              value={initialCapital}
              onChange={(e) => setInitialCapital(e.target.value)}
              disabled={submitting}
            />
          </label>

          <label className="flex flex-col gap-1.5 text-xs">
            <span className="uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">
              Start Date
            </span>
            <Input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              disabled={submitting}
            />
          </label>

          <label className="flex flex-col gap-1.5 text-xs">
            <span className="uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">
              End Date
            </span>
            <Input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              disabled={submitting}
            />
          </label>

          <div className="flex items-end">
            <Button type="submit" isLoading={submitting} className="w-full">
              Run Backtest
            </Button>
          </div>
        </form>

        {statusText ? (
          <p className="mt-4 text-sm text-[var(--nq-text-secondary)]">{statusText}</p>
        ) : null}
        {error ? (
          <p className="mt-4 text-sm text-[var(--nq-accent-red)]">{error}</p>
        ) : null}
      </section>
    </main>
  );
}
