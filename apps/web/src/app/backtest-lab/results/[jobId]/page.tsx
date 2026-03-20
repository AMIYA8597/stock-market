"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { contractsApi, type BacktestResultsResponse } from "@/lib/contracts-api";

function pct(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

export default function BacktestResultPage(): JSX.Element {
  const params = useParams<{ jobId: string }>();
  const jobId = params?.jobId ?? "unknown";
  const [result, setResult] = useState<BacktestResultsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);
      try {
        const response = await contractsApi.getBacktestResults(jobId);
        if (!mounted) {
          return;
        }
        setResult(response);
      } catch (requestError) {
        if (!mounted) {
          return;
        }
        const message = requestError instanceof Error ? requestError.message : "Failed to load backtest result.";
        setError(message);
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      mounted = false;
    };
  }, [jobId]);

  const foldSharpes = useMemo(() => result?.walk_forward?.fold_sharpes ?? [], [result]);

  return (
    <main className="min-h-screen bg-[var(--nq-bg-base)] p-8 text-[var(--nq-text-primary)]">
      <h1 className="text-2xl font-semibold">Backtest Result: {jobId}</h1>
      <p className="mt-2 text-sm text-[var(--nq-text-secondary)]">Metrics, equity curve, drawdown, and walk-forward outputs.</p>
      {error ? <p className="mt-2 text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <section className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Total Return", result ? pct(result.metrics.total_return) : "--"],
          ["CAGR", result ? pct(result.metrics.cagr) : "--"],
          ["Sharpe", result ? result.metrics.sharpe.toFixed(3) : "--"],
          ["Max Drawdown", result ? pct(result.metrics.max_drawdown) : "--"],
        ].map(([label, value]) => (
          <div key={label} className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3">
            <p className="text-xs text-[var(--nq-text-secondary)]">{label}</p>
            <p className="mt-1 text-lg font-semibold">{loading ? "..." : value}</p>
          </div>
        ))}
      </section>

      <section className="mt-6 grid gap-4 xl:grid-cols-2">
        <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Equity Curve</h2>
          <div className="h-44 rounded bg-[rgba(255,255,255,0.03)] p-2">
            <div className="flex h-full items-end gap-[2px]">
              {(result?.equity_curve ?? []).slice(-96).map((point) => {
                const h = Math.max(8, Math.min(100, (point.portfolio_value / Math.max(point.benchmark_value, 1)) * 45));
                return <div key={`eq-${point.date}`} className="w-full rounded-sm bg-[var(--nq-accent-green)]/56" style={{ height: `${h}%` }} />;
              })}
              {!loading && (!result || result.equity_curve.length === 0) ? <p className="m-auto text-xs text-[var(--nq-text-secondary)]">No equity data available.</p> : null}
            </div>
          </div>
        </article>

        <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Drawdown Series</h2>
          <div className="h-44 rounded bg-[rgba(255,255,255,0.03)] p-2">
            <div className="flex h-full items-end gap-[2px]">
              {(result?.drawdown_series ?? []).slice(-96).map((point) => {
                const h = Math.max(8, Math.min(100, Math.abs(point.drawdown_pct) * 100));
                return <div key={`dd-${point.date}`} className="w-full rounded-sm bg-[var(--nq-accent-red)]/52" style={{ height: `${h}%` }} />;
              })}
              {!loading && (!result || result.drawdown_series.length === 0) ? <p className="m-auto text-xs text-[var(--nq-text-secondary)]">No drawdown data available.</p> : null}
            </div>
          </div>
        </article>
      </section>

      <section className="mt-6 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
        <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Walk-Forward Folds</h2>
        <div className="grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-4">
          {foldSharpes.map((sharpe, idx) => (
            <div key={`fold-${idx}`} className="rounded border border-[var(--nq-border)] px-3 py-2">
              <div className="flex items-center justify-between">
                <span>Fold {idx + 1}</span>
                <span>{sharpe.toFixed(2)}</span>
              </div>
            </div>
          ))}
          {!loading && foldSharpes.length === 0 ? <p className="text-[var(--nq-text-secondary)]">No walk-forward fold data returned.</p> : null}
        </div>
      </section>
    </main>
  );
}
