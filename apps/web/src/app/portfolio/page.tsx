"use client";

import { useEffect, useMemo, useState } from "react";
import { contractsApi, type PortfolioHolding, type PortfolioPerformancePoint, type PortfolioRiskMetrics } from "@/lib/contracts-api";
import { usePriceFeed } from "@/hooks/usePriceFeed";

const CURRENCY_FORMATTER = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 2,
  minimumFractionDigits: 2,
});

const PERCENT_FORMATTER = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 2,
  minimumFractionDigits: 2,
});

function formatMoney(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return `₹${CURRENCY_FORMATTER.format(value)}`;
}

function formatPct(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return `${value >= 0 ? "+" : ""}${PERCENT_FORMATTER.format(value)}%`;
}

export default function PortfolioPage(): JSX.Element {
  const [holdings, setHoldings] = useState<PortfolioHolding[]>([]);
  const [risk, setRisk] = useState<PortfolioRiskMetrics | null>(null);
  const [performance, setPerformance] = useState<PortfolioPerformancePoint[]>([]);
  const [totalReturn, setTotalReturn] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);
      const [holdingsRes, riskRes, perfRes] = await Promise.allSettled([
        contractsApi.getPortfolioHoldings(),
        contractsApi.getPortfolioRiskMetrics(),
        contractsApi.getPortfolioPerformance(),
      ]);

      if (!mounted) {
        return;
      }

      if (holdingsRes.status === "fulfilled") {
        setHoldings(holdingsRes.value.holdings);
      } else {
        setError("Unable to load portfolio holdings contract.");
      }

      if (riskRes.status === "fulfilled") {
        setRisk(riskRes.value);
      }

      if (perfRes.status === "fulfilled") {
        setPerformance(perfRes.value.series);
        setTotalReturn(perfRes.value.total_return);
      }

      setLoading(false);
    }

    void load();

    return () => {
      mounted = false;
    };
  }, []);

  const symbols = useMemo(() => holdings.map((holding) => holding.symbol.toUpperCase()), [holdings]);
  const { ticks, status } = usePriceFeed(symbols);

  const portfolioValue = useMemo(() => {
    return holdings.reduce((sum, holding) => {
      const livePrice = ticks.get(holding.symbol.toUpperCase())?.price ?? holding.ltp;
      return sum + livePrice * holding.quantity;
    }, 0);
  }, [holdings, ticks]);

  const totalUnrealized = useMemo(() => {
    return holdings.reduce((sum, holding) => {
      const livePrice = ticks.get(holding.symbol.toUpperCase())?.price ?? holding.ltp;
      return sum + (livePrice - holding.avg_buy_price) * holding.quantity;
    }, 0);
  }, [holdings, ticks]);

  const performanceBars = useMemo(() => {
    const values = performance.slice(-120).map((point) => point.portfolio_value);
    if (values.length === 0) {
      return [] as number[];
    }
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = Math.max(max - min, 1e-9);
    return values.map((value) => 8 + ((value - min) / range) * 84);
  }, [performance]);

  return (
    <main className="min-h-screen bg-[var(--nq-bg-base)] p-6 text-[var(--nq-text-primary)]">
      <h1 className="mb-2 text-2xl font-semibold">Portfolio</h1>
      <p className="mb-4 text-xs text-[var(--nq-text-secondary)]">Live contracts: portfolio holdings, risk metrics, performance, and ws price feed ({status}).</p>
      {error ? <p className="mb-2 text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Portfolio Value", formatMoney(portfolioValue)],
          ["Unrealized PnL", formatMoney(totalUnrealized)],
          ["Total Return", formatPct(totalReturn)],
          ["Beta", typeof risk?.beta === "number" ? risk.beta.toFixed(2) : "--"],
        ].map(([key, value]) => (
          <div key={key} className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3">
            <div className="text-xs text-[var(--nq-text-secondary)]">{key}</div>
            <div className="mt-1 text-sm font-semibold">{value}</div>
          </div>
        ))}
      </section>

      <section className="mt-6 grid gap-4 xl:grid-cols-[2fr_1fr]">
        <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Holdings</h2>
          <table className="min-w-full text-xs">
            <thead>
              <tr className="text-[var(--nq-text-secondary)]">
                <th className="pb-2 text-left font-medium">Ticker</th>
                <th className="pb-2 text-right font-medium">Quantity</th>
                <th className="pb-2 text-right font-medium">Price</th>
                <th className="pb-2 text-right font-medium">Unrealized</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((holding) => {
                const livePrice = ticks.get(holding.symbol.toUpperCase())?.price ?? holding.ltp;
                const unrealized = (livePrice - holding.avg_buy_price) * holding.quantity;
                return (
                  <tr key={holding.symbol} className="border-t border-[var(--nq-border)]">
                    <td className="py-2">{holding.symbol}</td>
                    <td className="py-2 text-right">{holding.quantity.toLocaleString("en-IN")}</td>
                    <td className="py-2 text-right">{formatMoney(livePrice)}</td>
                    <td className="py-2 text-right">{formatMoney(unrealized)}</td>
                  </tr>
                );
              })}
              {!loading && holdings.length === 0 ? (
                <tr>
                  <td className="py-3 text-[var(--nq-text-secondary)]" colSpan={4}>No holdings returned by portfolio contract.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </article>

        <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Risk Metrics</h2>
          <div className="space-y-2 text-xs">
            {[
              ["Sharpe", typeof risk?.sharpe === "number" ? risk.sharpe.toFixed(2) : "--"],
              ["Sortino", typeof risk?.sortino === "number" ? risk.sortino.toFixed(2) : "--"],
              ["VaR (95)", formatPct(risk?.var_95)],
              ["CVaR (95)", formatPct(risk?.cvar_95)],
              ["Alpha", typeof risk?.alpha === "number" ? risk.alpha.toFixed(2) : "--"],
            ].map(([key, value]) => (
              <div key={key} className="flex items-center justify-between rounded bg-[rgba(255,255,255,0.02)] px-2 py-1">
                <span>{key}</span>
                <span>{value}</span>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="mt-6 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
        <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Performance vs Benchmark</h2>
        <div className="h-44 rounded bg-[rgba(255,255,255,0.03)] p-2">
          <div className="flex h-full items-end gap-[2px]">
            {(loading ? Array.from({ length: 90 }, () => 20) : performanceBars).map((height, index) => (
              <div key={`perf-${index}`} className="w-full rounded-sm bg-[var(--nq-accent-green)]/54" style={{ height: `${height}%` }} />
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}