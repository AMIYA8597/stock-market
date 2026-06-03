"use client";

import { useMemo, useState } from "react";
import { useEffect } from "react";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader, CardTitle } from "@/components/dashboard/premium";
import { contractsApi, type PortfolioOptimizeResponse } from "@/lib/contracts-api";
import {
  ChartCard,
  SimpleScatterFrontier,
  type FrontierPoint,
  SimpleDonutChart,
  type DonutSlice,
} from "@/components/charts";

const DEFAULT_UNIVERSE = "RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,ICICIBANK.NS,LT.NS,ITC.NS";

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

export default function PortfolioOptimizerPage(): JSX.Element {
  const [universeRaw, setUniverseRaw] = useState<string>(DEFAULT_UNIVERSE);
  const [method, setMethod] = useState<"hrp" | "black_litterman" | "cvar" | "mean_variance">("hrp");
  const [maxWeight, setMaxWeight] = useState<number>(0.2);
  const [maxTurnover, setMaxTurnover] = useState<number>(0.3);
  const [useMlViews, setUseMlViews] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PortfolioOptimizeResponse | null>(null);
  const [suggestedUniverse, setSuggestedUniverse] = useState<string[]>([]);

  useEffect(() => {
    let mounted = true;

    async function loadUniverseCandidates(): Promise<void> {
      try {
        const movers = await contractsApi.getMovers("NSE", "momentum");
        if (!mounted || movers.length === 0) {
          return;
        }
        const candidates = movers.slice(0, 12).map((item) => item.ticker.toUpperCase());
        setSuggestedUniverse(candidates);
        setUniverseRaw(candidates.join(","));
      } catch {
        // Keep seeded default if live candidates are unavailable.
      }
    }

    void loadUniverseCandidates();

    return () => {
      mounted = false;
    };
  }, []);

  const weightsRows = useMemo(() => {
    if (!result) {
      return [] as Array<[string, number]>;
    }
    return Object.entries(result.weights).sort((a, b) => b[1] - a[1]);
  }, [result]);

  const frontierPoints = useMemo<FrontierPoint[]>(() => {
    if (!result || result.efficient_frontier.length === 0) {
      return [];
    }
    return result.efficient_frontier.map((point, idx) => ({
      risk: point.vol,
      ret: point.return,
      highlight: idx === result.efficient_frontier.length - 1,
    }));
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

  const handleOptimize = async (): Promise<void> => {
    setLoading(true);
    setError(null);

    const universe = universeRaw
      .split(",")
      .map((symbol) => symbol.trim())
      .filter((symbol) => symbol.length > 0);

    if (universe.length === 0) {
      setError("Please provide at least one symbol.");
      setLoading(false);
      return;
    }

    try {
      const response = await contractsApi.optimizePortfolio({
        universe,
        method,
        constraints: {
          max_weight: maxWeight,
          max_turnover: maxTurnover,
        },
        use_ml_views: useMlViews,
      });
      setResult(response);
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Failed to optimize portfolio.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.main
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.26, ease: "easeOut" }}
      className="min-h-screen bg-[radial-gradient(1000px_500px_at_0%_0%,rgba(0,212,245,0.12),transparent_45%),radial-gradient(900px_420px_at_100%_0%,rgba(139,92,246,0.10),transparent_45%),var(--nq-bg-base)] p-4 text-[var(--nq-text-primary)] sm:p-6"
    >
      <section className="mb-6 grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Card glow className="relative overflow-hidden px-6 py-6 sm:px-8">
          <div className="absolute inset-0 bg-[radial-gradient(1000px_420px_at_0%_0%,rgba(0,212,245,0.16),transparent_45%),radial-gradient(800px_360px_at_100%_0%,rgba(139,92,246,0.14),transparent_45%)]" />
          <div className="relative space-y-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="bull" className="px-3 py-1.5 text-[10px] uppercase tracking-[0.16em]">Portfolio optimizer</Badge>
              <Badge variant="outline" className="px-3 py-1.5 text-[10px] uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">HRP · BL · CVaR · MVO</Badge>
            </div>
            <h1 className="text-4xl font-semibold tracking-tight text-[var(--nq-text-primary)] sm:text-5xl">Interactive allocation design with a clean risk-return frontier.</h1>
            <p className="max-w-2xl text-sm leading-7 text-[var(--nq-text-secondary)] sm:text-base">
              Adjust constraints, toggle ML views, and inspect the resulting weights, efficient frontier, and expected metrics in a single premium workspace.
            </p>
          </div>
        </Card>

        <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
          {[
            ["Universe", universeRaw.split(",").filter(Boolean).length.toString()],
            ["Method", method.replace("_", " ")],
            ["ML views", useMlViews ? "Enabled" : "Disabled"],
          ].map(([label, value]) => (
            <Card key={label} className="p-4">
              <CardHeader className="mb-3">
                <CardTitle className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">{label}</CardTitle>
              </CardHeader>
              <div className="text-lg font-semibold text-[var(--nq-text-primary)]">{value}</div>
            </Card>
          ))}
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[2fr_3fr]">
        <section className="rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-5 shadow-[0_18px_48px_rgba(0,0,0,0.22)]">
          <h2 className="mb-4 text-sm font-medium uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Inputs</h2>
          <div className="space-y-3 text-sm">
            <label className="block">
              <span className="mb-1 block text-xs text-[var(--nq-text-secondary)]">Universe</span>
              <textarea
                className="h-20 w-full rounded-[1rem] border border-white/10 bg-[var(--nq-bg-base)] px-3 py-2 text-[var(--nq-text-primary)] outline-none transition focus:border-[var(--nq-accent)]"
                value={universeRaw}
                onChange={(event) => setUniverseRaw(event.target.value)}
              />
              {suggestedUniverse.length > 0 ? (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {suggestedUniverse.slice(0, 8).map((symbol) => (
                    <button
                      key={symbol}
                      type="button"
                      onClick={() => setUniverseRaw((prev) => (prev.includes(symbol) ? prev : `${prev},${symbol}`))}
                      className="rounded-full border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[10px] text-[var(--nq-text-secondary)] transition hover:border-[var(--nq-accent)] hover:text-[var(--nq-text-primary)]"
                    >
                      {symbol}
                    </button>
                  ))}
                </div>
              ) : null}
            </label>

            <label className="block">
              <span className="mb-1 block text-xs text-[var(--nq-text-secondary)]">Method</span>
              <select
                className="w-full rounded-[1rem] border border-white/10 bg-[var(--nq-bg-base)] px-3 py-2 text-[var(--nq-text-primary)] outline-none transition focus:border-[var(--nq-accent)]"
                value={method}
                onChange={(event) => setMethod(event.target.value as "hrp" | "black_litterman" | "cvar" | "mean_variance")}
              >
                <option value="hrp">HRP</option>
                <option value="black_litterman">Black-Litterman</option>
                <option value="cvar">CVaR</option>
                <option value="mean_variance">Mean-Variance</option>
              </select>
            </label>

            <div className="rounded-[1rem] border border-white/10 bg-[rgba(255,255,255,0.04)] p-3 text-xs">
              <label className="mb-2 flex items-center justify-between">
                <span className="text-[var(--nq-text-secondary)]">Max Weight</span>
                <span>{formatPercent(maxWeight)}</span>
              </label>
              <input
                type="range"
                min={5}
                max={35}
                value={Math.round(maxWeight * 100)}
                onChange={(event) => setMaxWeight(Number(event.target.value) / 100)}
                className="w-full"
              />

              <label className="mb-2 mt-3 flex items-center justify-between">
                <span className="text-[var(--nq-text-secondary)]">Turnover Limit</span>
                <span>{maxTurnover.toFixed(2)}</span>
              </label>
              <input
                type="range"
                min={5}
                max={60}
                value={Math.round(maxTurnover * 100)}
                onChange={(event) => setMaxTurnover(Number(event.target.value) / 100)}
                className="w-full"
              />
            </div>

            <label className="flex items-center justify-between rounded border border-[var(--nq-border)] px-3 py-2 text-xs">
              <span className="text-[var(--nq-text-secondary)]">Use ML Views</span>
              <input type="checkbox" checked={useMlViews} onChange={(event) => setUseMlViews(event.target.checked)} className="h-4 w-4" />
            </label>

            <button
              className="w-full rounded-[1rem] bg-[linear-gradient(135deg,var(--nq-accent),#69f5ff)] px-4 py-2 text-sm font-semibold text-[#061219] shadow-[0_14px_28px_rgba(0,212,245,0.28)] transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-70"
              onClick={() => {
                void handleOptimize();
              }}
              disabled={loading}
            >
              {loading ? "Optimizing..." : "Optimize Portfolio"}
            </button>

            {error ? <p className="text-xs text-[var(--nq-accent-red)]">{error}</p> : null}
          </div>
        </section>

        <section className="space-y-4">
          <ChartCard title="Efficient Frontier" subtitle="Risk vs return points (highlight = optimized point)">
            <div className="relative h-52 rounded-[1rem] bg-[rgba(255,255,255,0.03)] p-1">
              {frontierPoints.length > 0 ? (
                <SimpleScatterFrontier points={frontierPoints} />
              ) : (
                <p className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-xs text-[var(--nq-text-secondary)]">Run optimization to render frontier.</p>
              )}
            </div>
          </ChartCard>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_1fr]">
            <Card className="p-4">
              <CardHeader>
                <CardTitle className="text-sm font-medium uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Expected Metrics</CardTitle>
              </CardHeader>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="rounded-[1rem] border border-white/10 p-2">
                  <div className="text-[var(--nq-text-secondary)]">Expected Return</div>
                  <div className="font-semibold">{result ? formatPercent(result.expected_return) : "--"}</div>
                </div>
                <div className="rounded-[1rem] border border-white/10 p-2">
                  <div className="text-[var(--nq-text-secondary)]">Expected Vol</div>
                  <div className="font-semibold">{result ? formatPercent(result.expected_vol) : "--"}</div>
                </div>
                <div className="rounded-[1rem] border border-white/10 p-2">
                  <div className="text-[var(--nq-text-secondary)]">Sharpe</div>
                  <div className="font-semibold">{result ? result.sharpe_ratio.toFixed(3) : "--"}</div>
                </div>
                <div className="rounded-[1rem] border border-white/10 p-2">
                  <div className="text-[var(--nq-text-secondary)]">Assets</div>
                  <div className="font-semibold">{weightsRows.length}</div>
                </div>
              </div>
            </Card>

            <Card className="p-4">
              <CardHeader>
                <CardTitle className="text-sm font-medium uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Allocation Summary</CardTitle>
              </CardHeader>
              <div className="grid gap-3 xl:grid-cols-[1fr_1fr]">
                <div className="h-36 rounded-[1rem] bg-[rgba(255,255,255,0.03)] p-1">
                  {donutSlices.length > 0 ? <SimpleDonutChart data={donutSlices} centerLabel="weights" /> : null}
                </div>
                <div className="space-y-2 text-xs text-[var(--nq-text-secondary)]">
                  {weightsRows.slice(0, 6).map(([ticker, weight]) => (
                    <div key={ticker} className="flex items-center justify-between rounded-[1rem] border border-white/10 px-2 py-1">
                      <span>{ticker}</span>
                      <span>{formatPercent(weight)}</span>
                    </div>
                  ))}
                  {weightsRows.length === 0 ? <div className="rounded-[1rem] border border-white/10 px-2 py-1">No optimization response yet.</div> : null}
                </div>
              </div>
            </Card>
          </div>

          <div className="rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-4">
            <h2 className="mb-3 text-sm font-medium uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Weights</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full text-xs">
                <thead>
                  <tr className="text-[var(--nq-text-secondary)]">
                    <th className="pb-2 text-left font-medium">Ticker</th>
                    <th className="pb-2 text-right font-medium">Weight</th>
                  </tr>
                </thead>
                <tbody>
                  {weightsRows.map(([ticker, weight]) => (
                    <tr key={ticker} className="border-t border-[var(--nq-border)]">
                      <td className="py-2">{ticker}</td>
                      <td className="py-2 text-right">{formatPercent(weight)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>
    </motion.main>
  );
}
