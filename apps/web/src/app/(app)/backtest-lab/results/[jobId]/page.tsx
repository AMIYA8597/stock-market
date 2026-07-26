/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import {
  contractsApi,
  type BacktestResultsResponse,
} from "@/lib/contracts-api";
import { Badge } from "@neuroquant/ui";
import { ChartCard } from "@/components/charts";
import { formatRatioPercent, safeFormat } from "@/lib/formatters";

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
        const message =
          requestError instanceof Error
            ? requestError.message
            : "Failed to load backtest result.";
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

  const foldSharpes = useMemo(
    () => result?.walk_forward?.fold_sharpes ?? [],
    [result],
  );

  const tradeLog = useMemo(() => result?.trade_log ?? [], [result]);

  const monthlyReturns = useMemo(() => {
    if (!result || result.equity_curve.length === 0) return [];

    const eodByMonth: Record<string, number> = {};
    for (const pt of result.equity_curve) {
      const d = new Date(pt.date);
      const yyyy = d.getFullYear();
      const mm = String(d.getMonth() + 1).padStart(2, "0");
      eodByMonth[`${yyyy}-${mm}`] = pt.portfolio_value;
    }

    const returns: { year: number; month: number; ret: number }[] = [];
    const months = Object.keys(eodByMonth).sort();

    let prevValue = result.equity_curve[0]?.portfolio_value ?? 1; // base for first month

    for (let i = 0; i < months.length; i++) {
      const monthKey = months[i];
      if (!monthKey) continue;
      const curr = eodByMonth[monthKey];
      if (curr === undefined) continue;
      
      const [yyyy, mm] = monthKey.split("-").map(Number) as [number, number];
      returns.push({
        year: yyyy,
        month: mm,
        ret: curr / prevValue - 1,
      });
      prevValue = curr;
    }

    return returns;
  }, [result]);

  const heatmapByYear = useMemo(() => {
    const byYear: Record<number, (number | null)[]> = {};
    for (const r of monthlyReturns) {
      if (!byYear[r.year]) byYear[r.year] = Array(12).fill(null);
      const arr = byYear[r.year];
      if (arr) {
        arr[r.month - 1] = r.ret;
      }
    }
    return Object.entries(byYear)
      .map(([y, arr]) => ({ year: Number(y), returns: arr }))
      .sort((a, b) => b.year - a.year); // newest first
  }, [monthlyReturns]);

  return (
    <main className="min-h-screen bg-[radial-gradient(1000px_500px_at_0%_0%,rgba(0,212,245,0.12),transparent_45%),radial-gradient(900px_420px_at_100%_0%,rgba(139,92,246,0.10),transparent_45%),var(--nq-bg-base)] p-4 text-[var(--nq-text-primary)] sm:p-6 lg:p-8">
      <section className="mb-6 rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-5 shadow-[0_18px_48px_rgba(0,0,0,0.22)]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                variant="bull"
                className="px-3 py-1.5 text-[10px] uppercase tracking-[0.16em]"
              >
                Backtest results
              </Badge>
              <Badge
                variant="outline"
                className="px-3 py-1.5 text-[10px] uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]"
              >
                Walk-forward + Monte Carlo
              </Badge>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-[var(--nq-text-primary)] sm:text-4xl">
              Backtest Result: {jobId}
            </h1>
            <p className="text-sm text-[var(--nq-text-secondary)]">
              Metrics, equity curve, drawdown, and walk-forward outputs rendered
              in a clean verification-ready layout.
            </p>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="rounded-[1rem] border border-white/10 bg-white/[0.04] px-3 py-2 text-xs">
              <p className="text-[var(--nq-text-secondary)]">Status</p>
              <p className="mt-1 font-medium">
                {loading ? "Loading" : error ? "Error" : "Ready"}
              </p>
            </div>
            <div className="rounded-[1rem] border border-white/10 bg-white/[0.04] px-3 py-2 text-xs">
              <p className="text-[var(--nq-text-secondary)]">Loaded folds</p>
              <p className="mt-1 font-medium">{foldSharpes.length}</p>
            </div>
          </div>
        </div>
      </section>
      {error ? (
        <p className="mt-2 text-sm text-[var(--nq-accent-red)]">{error}</p>
      ) : null}

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Total Return", result ? formatRatioPercent(result.metrics.total_return) : "--"],
          ["CAGR", result ? formatRatioPercent(result.metrics.cagr) : "--"],
          ["Sharpe", result ? safeFormat(result.metrics.sharpe, 3) : "--"],
          ["Max Drawdown", result ? formatRatioPercent(result.metrics.max_drawdown) : "--"],
        ].map(([label, value]) => (
          <div
            key={label}
            className="rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3"
          >
            <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">
              {label}
            </p>
            <p className="mt-2 text-lg font-semibold text-[var(--nq-text-primary)]">
              {loading ? "..." : value}
            </p>
          </div>
        ))}
      </section>

      <section className="mt-6 grid gap-4 xl:grid-cols-2">
        <ChartCard title="Equity Curve" subtitle="Portfolio value vs benchmark">
          <div className="h-44 rounded-[1rem] bg-[rgba(255,255,255,0.03)] p-2">
            <div className="flex h-full items-end gap-[2px]">
              {(result?.equity_curve ?? []).slice(-96).map((point) => {
                const h = Math.max(
                  8,
                  Math.min(
                    100,
                    (point.portfolio_value /
                      Math.max(point.benchmark_value, 1)) *
                      45,
                  ),
                );
                return (
                  <div
                    key={`eq-${point.date}`}
                    className="w-full rounded-sm bg-[var(--nq-accent-green)]/56"
                    style={{ height: `${h}%` }}
                  />
                );
              })}
              {!loading && (!result || result.equity_curve.length === 0) ? (
                <p className="m-auto text-xs text-[var(--nq-text-secondary)]">
                  No equity data available.
                </p>
              ) : null}
            </div>
          </div>
        </ChartCard>

        <ChartCard
          title="Drawdown Series"
          subtitle="Underwater equity pressure"
        >
          <div className="h-44 rounded-[1rem] bg-[rgba(255,255,255,0.03)] p-2">
            <div className="flex h-full items-end gap-[2px]">
              {(result?.drawdown_series ?? []).slice(-96).map((point) => {
                const h = Math.max(
                  8,
                  Math.min(100, Math.abs(point.drawdown_pct) * 100),
                );
                return (
                  <div
                    key={`dd-${point.date}`}
                    className="w-full rounded-sm bg-[var(--nq-accent-red)]/52"
                    style={{ height: `${h}%` }}
                  />
                );
              })}
              {!loading && (!result || result.drawdown_series.length === 0) ? (
                <p className="m-auto text-xs text-[var(--nq-text-secondary)]">
                  No drawdown data available.
                </p>
              ) : null}
            </div>
          </div>
        </ChartCard>
      </section>

      <section className="mt-6 rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-4">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">
          Walk-Forward Folds
        </h2>
        <div className="grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-4">
          {foldSharpes.map((sharpe, idx) => (
            <div
              key={`fold-${idx}`}
              className="rounded-[1rem] border border-white/10 bg-white/[0.04] px-3 py-2"
            >
              <div className="flex items-center justify-between text-[var(--nq-text-primary)]">
                <span>Fold {idx + 1}</span>
                <span
                  className={
                    Number(sharpe) >= 0
                      ? "text-[var(--nq-bull)]"
                      : "text-[var(--nq-bear)]"
                  }
                >
                  {safeFormat(sharpe, 2)}
                </span>
              </div>
            </div>
          ))}
          {!loading && foldSharpes.length === 0 ? (
            <p className="text-[var(--nq-text-secondary)]">
              No walk-forward fold data returned.
            </p>
          ) : null}
        </div>
      </section>

      <section className="mt-6 rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-4 overflow-x-auto ds-scrollable">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">
          Monthly Returns Heatmap
        </h2>
        <div className="min-w-[600px] text-xs">
          <div className="grid grid-cols-[60px_repeat(12,1fr)] gap-1 mb-2 font-semibold text-[var(--nq-text-secondary)] text-center">
            <div className="text-left">Year</div>
            {["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].map((m) => (
              <div key={m}>{m}</div>
            ))}
          </div>
          {heatmapByYear.map((row) => (
            <div key={row.year} className="grid grid-cols-[60px_repeat(12,1fr)] gap-1 mb-1 items-center">
              <div className="font-semibold text-[var(--nq-text-primary)]">{row.year}</div>
              {row.returns.map((ret, idx) => {
                if (ret === null) {
                  return <div key={idx} className="h-8 rounded bg-[rgba(255,255,255,0.02)]" />;
                }
                const isPositive = ret > 0;
                const alpha = Math.min(0.8, Math.abs(ret) * 5); // scale opacity by return magnitude
                const bgColor = isPositive ? `rgba(0,230,118,${alpha})` : `rgba(255,59,92,${alpha})`;
                return (
                  <div
                    key={idx}
                    className="h-8 rounded flex items-center justify-center font-mono text-[10px] text-white"
                    style={{ backgroundColor: bgColor }}
                    title={`${row.year}-${String(idx + 1).padStart(2, "0")}: ${formatRatioPercent(ret)}`}
                  >
                    {formatRatioPercent(ret)}
                  </div>
                );
              })}
            </div>
          ))}
          {!loading && heatmapByYear.length === 0 ? (
            <p className="text-[var(--nq-text-secondary)] mt-2">No monthly returns computed.</p>
          ) : null}
        </div>
      </section>

      <section className="mt-6 rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-4 overflow-x-auto ds-scrollable">
        <h2 className="mb-3 text-sm font-medium uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">
          Trade Log (Sample)
        </h2>
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-[var(--nq-bg-card-hover)] text-[var(--nq-text-secondary)]">
            <tr>
              <th className="px-3 py-2 font-medium">Date</th>
              <th className="px-3 py-2 font-medium">Symbol</th>
              <th className="px-3 py-2 font-medium">Dir</th>
              <th className="px-3 py-2 font-medium text-right">Price</th>
              <th className="px-3 py-2 font-medium text-right">Qty</th>
              <th className="px-3 py-2 font-medium text-right">PnL</th>
              <th className="px-3 py-2 font-medium text-right">Cum PnL</th>
            </tr>
          </thead>
          <tbody>
            {tradeLog.map((trade: any, idx: number) => (
              <tr key={`trade-${idx}`} className="border-t border-[var(--nq-border)] hover:bg-[rgba(255,255,255,0.01)] transition-colors">
                <td className="px-3 py-2">{new Date(trade.date).toLocaleDateString()}</td>
                <td className="px-3 py-2 text-[var(--nq-text-primary)]">{trade.symbol}</td>
                <td className={`px-3 py-2 font-bold ${trade.direction === "LONG" ? "text-[var(--nq-bull)]" : "text-[var(--nq-bear)]"}`}>
                  {trade.direction}
                </td>
                <td className="px-3 py-2 text-right">{safeFormat(trade.price, 2)}</td>
                <td className="px-3 py-2 text-right">{safeFormat(trade.quantity, 2)}</td>
                <td className={`px-3 py-2 text-right font-bold ${trade.pnl > 0 ? "text-[var(--nq-bull)]" : trade.pnl < 0 ? "text-[var(--nq-bear)]" : "text-[var(--nq-text-secondary)]"}`}>
                  {trade.pnl > 0 ? "+" : ""}{safeFormat(trade.pnl, 2)}
                </td>
                <td className="px-3 py-2 text-right text-[var(--nq-text-primary)]">{safeFormat(trade.cum_pnl, 2)}</td>
              </tr>
            ))}
            {!loading && tradeLog.length === 0 ? (
              <tr className="border-t border-[var(--nq-border)]">
                <td colSpan={7} className="px-3 py-4 text-center text-[var(--nq-text-secondary)] italic">
                  No trades recorded.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </section>
    </main>
  );
}
