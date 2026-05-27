"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { contractsApi, type BacktestResultsResponse } from "@/lib/contracts-api";
import { Badge } from "@/components/ui/Badge";
import { ChartCard } from "@/components/charts";

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
    <main className="min-h-screen bg-[radial-gradient(1000px_500px_at_0%_0%,rgba(0,212,245,0.12),transparent_45%),radial-gradient(900px_420px_at_100%_0%,rgba(139,92,246,0.10),transparent_45%),var(--nq-bg-base)] p-4 text-[var(--nq-text-primary)] sm:p-6 lg:p-8">
      <section className="mb-6 rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-5 shadow-[0_18px_48px_rgba(0,0,0,0.22)]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="bull" className="px-3 py-1.5 text-[10px] uppercase tracking-[0.16em]">Backtest results</Badge>
              <Badge variant="outline" className="px-3 py-1.5 text-[10px] uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">Walk-forward + Monte Carlo</Badge>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-[var(--nq-text-primary)] sm:text-4xl">Backtest Result: {jobId}</h1>
            <p className="text-sm text-[var(--nq-text-secondary)]">Metrics, equity curve, drawdown, and walk-forward outputs rendered in a clean verification-ready layout.</p>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="rounded-[1rem] border border-white/10 bg-white/[0.04] px-3 py-2 text-xs">
              <p className="text-[var(--nq-text-secondary)]">Status</p>
              <p className="mt-1 font-medium">{loading ? "Loading" : error ? "Error" : "Ready"}</p>
            </div>
            <div className="rounded-[1rem] border border-white/10 bg-white/[0.04] px-3 py-2 text-xs">
              <p className="text-[var(--nq-text-secondary)]">Loaded folds</p>
              <p className="mt-1 font-medium">{foldSharpes.length}</p>
            </div>
          </div>
        </div>
      </section>
      {error ? <p className="mt-2 text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Total Return", result ? pct(result.metrics.total_return) : "--"],
          ["CAGR", result ? pct(result.metrics.cagr) : "--"],
          ["Sharpe", result ? result.metrics.sharpe.toFixed(3) : "--"],
          ["Max Drawdown", result ? pct(result.metrics.max_drawdown) : "--"],
        ].map(([label, value]) => (
          <div key={label} className="rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3">
            <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">{label}</p>
            <p className="mt-2 text-lg font-semibold text-[var(--nq-text-primary)]">{loading ? "..." : value}</p>
          </div>
        ))}
      </section>

      <section className="mt-6 grid gap-4 xl:grid-cols-2">
        <ChartCard title="Equity Curve" subtitle="Portfolio value vs benchmark">
          <div className="h-44 rounded-[1rem] bg-[rgba(255,255,255,0.03)] p-2">
            <div className="flex h-full items-end gap-[2px]">
              {(result?.equity_curve ?? []).slice(-96).map((point) => {
                const h = Math.max(8, Math.min(100, (point.portfolio_value / Math.max(point.benchmark_value, 1)) * 45));
                return <div key={`eq-${point.date}`} className="w-full rounded-sm bg-[var(--nq-accent-green)]/56" style={{ height: `${h}%` }} />;
              })}
              {!loading && (!result || result.equity_curve.length === 0) ? <p className="m-auto text-xs text-[var(--nq-text-secondary)]">No equity data available.</p> : null}
            </div>
          </div>
        </ChartCard>

        <ChartCard title="Drawdown Series" subtitle="Underwater equity pressure">
          <div className="h-44 rounded-[1rem] bg-[rgba(255,255,255,0.03)] p-2">
            <div className="flex h-full items-end gap-[2px]">
              {(result?.drawdown_series ?? []).slice(-96).map((point) => {
                const h = Math.max(8, Math.min(100, Math.abs(point.drawdown_pct) * 100));
                return <div key={`dd-${point.date}`} className="w-full rounded-sm bg-[var(--nq-accent-red)]/52" style={{ height: `${h}%` }} />;
              })}
              {!loading && (!result || result.drawdown_series.length === 0) ? <p className="m-auto text-xs text-[var(--nq-text-secondary)]">No drawdown data available.</p> : null}
            </div>
          </div>
        </ChartCard>
      </section>

      <section className="mt-6 rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-4">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Walk-Forward Folds</h2>
        <div className="grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-4">
          {foldSharpes.map((sharpe, idx) => (
            <div key={`fold-${idx}`} className="rounded-[1rem] border border-white/10 bg-white/[0.04] px-3 py-2">
              <div className="flex items-center justify-between text-[var(--nq-text-primary)]">
                <span>Fold {idx + 1}</span>
                <span className={sharpe >= 0 ? "text-[var(--nq-bull)]" : "text-[var(--nq-bear)]"}>{sharpe.toFixed(2)}</span>
              </div>
            </div>
          ))}
          {!loading && foldSharpes.length === 0 ? <p className="text-[var(--nq-text-secondary)]">No walk-forward fold data returned.</p> : null}
        </div>
      </section>
    </main>
  );
}
