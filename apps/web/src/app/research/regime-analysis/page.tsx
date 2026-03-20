"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { contractsApi, type RegimeCurrentResponse, type RegimeHistoryPoint, type RegimeStatisticsItem } from "@/lib/contracts-api";

const STATE_ORDER = ["BULL", "BEAR", "SIDEWAYS", "CRISIS"] as const;

function pct(value: number | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return `${(value * 100).toFixed(2)}%`;
}

export default function RegimeAnalysisPage(): JSX.Element {
  const [current, setCurrent] = useState<RegimeCurrentResponse | null>(null);
  const [history, setHistory] = useState<RegimeHistoryPoint[]>([]);
  const [statistics, setStatistics] = useState<RegimeStatisticsItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);

      const [currentRes, historyRes, statsRes] = await Promise.allSettled([
        contractsApi.getRegimeCurrent(),
        contractsApi.getRegimeHistory(180),
        contractsApi.getRegimeStatistics(),
      ]);

      if (!mounted) {
        return;
      }

      if (currentRes.status === "fulfilled") {
        setCurrent(currentRes.value);
      } else {
        setError("Unable to load regime current contract.");
      }

      if (historyRes.status === "fulfilled") {
        setHistory(historyRes.value);
      }

      if (statsRes.status === "fulfilled") {
        setStatistics(statsRes.value);
      }

      setLastUpdated(new Date().toISOString());

      setLoading(false);
    }

    void load();

    const timer = setInterval(() => {
      void load();
    }, 45_000);

    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  const currentStateProb = useMemo(() => {
    if (!current) {
      return undefined;
    }
    return current.probs[current.state];
  }, [current]);

  const transitionCells = useMemo(() => {
    return (current?.transition_matrix ?? []).flatMap((row, rowIdx) => row.map((value, colIdx) => ({ value, rowIdx, colIdx })));
  }, [current?.transition_matrix]);

  const historyBars = useMemo(() => {
    const recent = history.slice(-90);
    if (recent.length === 0) {
      return [] as number[];
    }

    const vols = recent.map((item) => item.cond_vol);
    const min = Math.min(...vols);
    const max = Math.max(...vols);
    const range = Math.max(max - min, 1e-9);

    return vols.map((vol) => 8 + ((vol - min) / range) * 86);
  }, [history]);

  const regimeBands = useMemo(() => {
    const recent = history.slice(-90);
    if (recent.length === 0) {
      return [] as Array<{ color: string; width: number }>;
    }

    const counts = STATE_ORDER.map((state) => recent.filter((item) => item.state === state).length);
    return counts.map((count, index) => {
      const width = (count / recent.length) * 100;
      const color =
        index === 0
          ? "var(--nq-regime-bull)"
          : index === 1
            ? "var(--nq-regime-bear)"
            : index === 2
              ? "var(--nq-regime-side)"
              : "var(--nq-regime-crisis)";
      return { color, width };
    });
  }, [history]);

  return (
    <motion.main
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="min-h-screen bg-[var(--nq-bg-base)] p-4 text-[var(--nq-text-primary)] sm:p-6"
    >
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Regime Analysis</h1>
        <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1 text-xs text-[var(--nq-text-secondary)]">
          Window: 180d | Updated: {lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : "--"}
        </div>
      </div>

      {error ? <p className="mb-3 text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[2fr_1fr]">
        <section className="space-y-4">
          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
            <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Regime Bands (Recent Distribution)</h2>
            <div className="relative h-[120px] overflow-hidden rounded bg-[rgba(255,255,255,0.02)]">
              <div className="absolute inset-0 flex">
                {(loading ? [{ color: "var(--nq-regime-bull)", width: 100 }] : regimeBands).map((band, index) => (
                  <div key={`band-${index}`} style={{ width: `${band.width}%`, backgroundColor: band.color }} />
                ))}
              </div>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
              {STATE_ORDER.map((state) => (
                <div key={state} className="rounded border border-[var(--nq-border)] px-2 py-1 text-center">
                  <span>{state}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
            <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Conditional Volatility Forecast</h2>
            <div className="h-[220px] rounded bg-[rgba(255,255,255,0.02)] p-2">
              <div className="flex h-full items-end gap-[2px]">
                {(loading ? Array.from({ length: 90 }, () => 18) : historyBars).map((height, idx) => (
                  <div key={`vol-${idx}`} className="w-full rounded-sm bg-[var(--nq-accent-red)]/55" style={{ height: `${height}%` }} />
                ))}
              </div>
            </div>
          </div>
        </section>

        <aside className="space-y-4">
          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
            <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Current State</h2>
            <div className="rounded border border-[rgba(0,230,118,0.4)] bg-[rgba(0,230,118,0.08)] p-3">
              <div className="text-lg font-semibold text-[var(--nq-accent-green)]">{loading ? "..." : current?.state ?? "--"}</div>
              <div className="mt-1 text-xs text-[var(--nq-text-secondary)]">Confidence: {loading ? "..." : pct(currentStateProb)}</div>
              <div className="mt-1 text-xs text-[var(--nq-text-secondary)]">Days in state: {loading ? "..." : (current?.days_in_state ?? "--")}</div>
              <div className="mt-1 text-xs text-[var(--nq-text-secondary)]">Last transition: {loading ? "..." : (current?.last_transition_date ?? "--")}</div>
            </div>
          </div>

          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
            <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Transition Matrix</h2>
            <div className="grid grid-cols-4 gap-2 text-center text-[11px]">
              {(loading
                ? Array.from({ length: 16 }, (_, index) => ({ value: 0.25, rowIdx: Math.floor(index / 4), colIdx: index % 4 }))
                : transitionCells
              ).map((cell) => (
                <div
                  key={`tm-${cell.rowIdx}-${cell.colIdx}`}
                  className="rounded border border-[var(--nq-border)] py-2"
                  style={{ background: `rgba(0,212,245,${0.08 + cell.value * 0.45})` }}
                >
                  {(cell.value * 100).toFixed(1)}%
                </div>
              ))}
            </div>
          </div>

          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
            <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">State Statistics</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full text-xs">
                <thead>
                  <tr className="text-[var(--nq-text-secondary)]">
                    <th className="pb-2 text-left font-medium">State</th>
                    <th className="pb-2 text-right font-medium">Dur.</th>
                    <th className="pb-2 text-right font-medium">Freq</th>
                    <th className="pb-2 text-right font-medium">Ret</th>
                    <th className="pb-2 text-right font-medium">Vol</th>
                  </tr>
                </thead>
                <tbody>
                  {statistics.map((row) => (
                    <tr key={row.state} className="border-t border-[var(--nq-border)]">
                      <td className="py-2">{row.state}</td>
                      <td className="py-2 text-right">{row.avg_duration.toFixed(1)}</td>
                      <td className="py-2 text-right">{pct(row.freq)}</td>
                      <td className="py-2 text-right">{pct(row.avg_return)}</td>
                      <td className="py-2 text-right">{pct(row.avg_vol)}</td>
                    </tr>
                  ))}
                  {!loading && statistics.length === 0 ? (
                    <tr>
                      <td className="py-2 text-[var(--nq-text-secondary)]" colSpan={5}>No regime statistics returned.</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </div>
        </aside>
      </div>
    </motion.main>
  );
}
