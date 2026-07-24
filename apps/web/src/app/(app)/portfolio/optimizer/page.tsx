/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
"use client";

import { useMemo, useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Badge, Card, CardHeader, CardTitle } from "@neuroquant/ui";
import { portfolioApi } from "@/lib/api-client";
import {
  SimpleDonutChart,
  type DonutSlice,
} from "@/components/charts";

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

export default function PortfolioOptimizerPage(): JSX.Element {
  const [method, setMethod] = useState<"hrp" | "max_sharpe" | "min_volatility" | "efficient_risk">("max_sharpe");
  const [targetReturn, setTargetReturn] = useState<number>(0.15);
  
  const { data: portfolios, isLoading: isLoadingPortfolios } = useQuery({
    queryKey: ["portfolios"],
    queryFn: () => portfolioApi.list()
  });

  const portfolioId = portfolios?.[0]?.id;

  const optimizeMutation = useMutation({
    mutationFn: () => {
      if (!portfolioId) throw new Error("No portfolio available.");
      return portfolioApi.optimize({
        portfolio_id: portfolioId,
        method,
        target_return: method === "efficient_risk" ? targetReturn : undefined,
      });
    }
  });

  const result = optimizeMutation.data;

  const weightsRows = useMemo(() => {
    if (!result || !result.weights) {
      return [] as Array<[string, number]>;
    }
    return Object.entries(result.weights).sort((a, b) => b[1] - a[1]);
  }, [result]);

  const donutSlices = useMemo<DonutSlice[]>(() => {
    const palette = [
      "rgba(0,212,245,0.85)",
      "rgba(0,230,118,0.85)",
      "rgba(139,92,246,0.85)",
      "rgba(255,184,0,0.85)",
      "rgba(255,59,92,0.85)",
      "rgba(226,238,250,0.85)",
    ];

    return weightsRows.slice(0, 8).map(([ticker, weight], idx) => ({
      name: ticker,
      value: weight,
      color: palette[idx % palette.length] ?? "rgba(0,212,245,0.85)",
    }));
  }, [weightsRows]);

  if (isLoadingPortfolios) {
    return (
      <main className="min-h-screen bg-[var(--nq-bg-base)] p-6 text-center text-sm text-[var(--nq-text-secondary)]">
        Loading optimizer...
      </main>
    );
  }

  if (!portfolioId) {
    return (
      <main className="min-h-screen bg-[var(--nq-bg-base)] p-6 flex flex-col items-center justify-center text-center">
        <h2 className="text-xl font-bold text-[var(--nq-text-primary)] mb-2">Portfolio Not Found</h2>
        <p className="text-sm text-[var(--nq-text-secondary)]">Add a portfolio to use the optimizer.</p>
      </main>
    );
  }

  return (
    <motion.main
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.26, ease: "easeOut" }}
      className="min-h-screen bg-[radial-gradient(1000px_500px_at_0%_0%,rgba(0,212,245,0.12),transparent_45%),radial-gradient(900px_420px_at_100%_0%,rgba(139,92,246,0.10),transparent_45%),var(--nq-bg-base)] p-4 text-[var(--nq-text-primary)] sm:p-6"
    >
      <section className="mb-6 grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="relative overflow-hidden px-6 py-6 sm:px-8">
          <div className="absolute inset-0 bg-[radial-gradient(1000px_420px_at_0%_0%,rgba(0,212,245,0.16),transparent_45%),radial-gradient(800px_360px_at_100%_0%,rgba(139,92,246,0.14),transparent_45%)]" />
          <div className="relative space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="bull" className="px-3 py-1.5 text-[10px] uppercase tracking-[0.16em]">Portfolio optimizer</Badge>
              <Badge variant="outline" className="px-3 py-1.5 text-[10px] uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">Real Data</Badge>
            </div>
            <h1 className="text-4xl font-semibold tracking-tight text-[var(--nq-text-primary)] sm:text-5xl">Interactive allocation design</h1>
            <p className="max-w-2xl text-sm leading-7 text-[var(--nq-text-secondary)] sm:text-base">
              Adjust constraints and inspect the resulting weights and expected metrics for your active portfolio.
            </p>
          </div>
        </Card>

        <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
          <Card className="p-4">
            <CardHeader className="mb-3">
              <CardTitle className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Method</CardTitle>
            </CardHeader>
            <div className="text-lg font-semibold text-[var(--nq-text-primary)] uppercase">
              {method.replace("_", " ")}
            </div>
          </Card>
          <Card className="p-4">
            <CardHeader className="mb-3">
              <CardTitle className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Risk-Free Rate</CardTitle>
            </CardHeader>
            <div className="text-lg font-semibold text-[var(--nq-text-primary)]">
              0.0%
            </div>
          </Card>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[2fr_3fr]">
        <section className="rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-5 shadow-[0_18px_48px_rgba(0,0,0,0.22)]">
          <h2 className="mb-4 text-sm font-medium uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Inputs</h2>
          <div className="space-y-3 text-sm">
            <label className="block">
              <span className="mb-1 block text-xs text-[var(--nq-text-secondary)]">Method</span>
              <select
                className="w-full rounded-[1rem] border border-white/10 bg-[var(--nq-bg-base)] px-3 py-2 text-[var(--nq-text-primary)] outline-none transition focus:border-[var(--nq-accent)]"
                value={method}
                onChange={(event) => setMethod(event.target.value as any)}
              >
                <option value="max_sharpe">Max Sharpe</option>
                <option value="min_volatility">Min Volatility</option>
                <option value="efficient_risk">Efficient Risk</option>
                <option value="hrp">HRP</option>
              </select>
            </label>

            {method === "efficient_risk" && (
              <div className="rounded-[1rem] border border-white/10 bg-[rgba(255,255,255,0.04)] p-3 text-xs">
                <label className="mb-2 flex items-center justify-between">
                  <span className="text-[var(--nq-text-secondary)]">Target Return</span>
                  <span>{formatPercent(targetReturn)}</span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={50}
                  value={Math.round(targetReturn * 100)}
                  onChange={(event) => setTargetReturn(Number(event.target.value) / 100)}
                  className="w-full"
                />
              </div>
            )}

            <button
              className="w-full rounded-[1rem] bg-[linear-gradient(135deg,var(--nq-accent),#69f5ff)] px-4 py-2 text-sm font-semibold text-[#061219] shadow-[0_14px_28px_rgba(0,212,245,0.28)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-70"
              onClick={() => optimizeMutation.mutate()}
              disabled={optimizeMutation.isPending}
            >
              {optimizeMutation.isPending ? "Optimizing..." : "Optimize Portfolio"}
            </button>

            {optimizeMutation.isError ? (
              <p className="text-xs text-[var(--nq-accent-red)]">
                {optimizeMutation.error.message || "Failed to optimize portfolio."}
              </p>
            ) : null}
          </div>
        </section>

        {result ? (
          <section className="grid gap-4 sm:grid-cols-2">
            <Card className="flex flex-col p-5">
              <h3 className="mb-4 text-xs font-semibold uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Target Weights</h3>
              {weightsRows.length > 0 ? (
                <div className="flex-1 overflow-auto pr-2">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-white/10 text-xs text-[var(--nq-text-secondary)]">
                        <th className="pb-2 font-medium">Asset</th>
                        <th className="pb-2 text-right font-medium">Weight</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {weightsRows.map(([ticker, weight], idx) => (
                        <tr key={ticker} className="transition hover:bg-white/[0.02]">
                          <td className="py-2.5">
                            <div className="flex items-center gap-2">
                              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: donutSlices[idx % donutSlices.length]?.color ?? "gray" }} />
                              <span className="font-semibold tracking-wide">{ticker}</span>
                            </div>
                          </td>
                          <td className="py-2.5 text-right font-mono text-[var(--nq-text-primary)]">
                            {formatPercent(weight)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="flex flex-1 items-center justify-center text-sm text-[var(--nq-text-secondary)]">
                  Empty portfolio.
                </div>
              )}
            </Card>

            <Card className="p-5 flex flex-col justify-between">
              <div>
                <h3 className="mb-4 text-xs font-semibold uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Metrics</h3>
                <div className="space-y-4 font-mono text-sm">
                  <div className="flex justify-between border-b border-white/5 pb-2">
                    <span className="text-[var(--nq-text-secondary)]">Exp. Return</span>
                    <span className="font-semibold text-[var(--nq-bull)]">
                      {formatPercent(result.expected_return)}
                    </span>
                  </div>
                  <div className="flex justify-between border-b border-white/5 pb-2">
                    <span className="text-[var(--nq-text-secondary)]">Exp. Volatility</span>
                    <span className="font-semibold text-[var(--nq-accent-cyan)]">
                      {formatPercent(result.expected_volatility)}
                    </span>
                  </div>
                  <div className="flex justify-between border-b border-white/5 pb-2">
                    <span className="text-[var(--nq-text-secondary)]">Sharpe Ratio</span>
                    <span className="font-semibold text-[var(--nq-text-primary)]">
                      {result.sharpe_ratio?.toFixed(3)}
                    </span>
                  </div>
                </div>
              </div>
              <div className="mt-6 flex justify-center">
                 <div className="h-[200px] w-full max-w-[200px]">
                  {donutSlices.length > 0 && <SimpleDonutChart data={donutSlices} />}
                 </div>
              </div>
            </Card>
          </section>
        ) : (
          <section className="flex items-center justify-center rounded-[1.5rem] border border-white/5 bg-[var(--nq-bg-card)]">
            <div className="text-center text-[var(--nq-text-secondary)]">
              <svg className="mx-auto h-8 w-8 opacity-40 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <p className="text-sm">Run optimizer to see results</p>
            </div>
          </section>
        )}
      </div>
    </motion.main>
  );
}