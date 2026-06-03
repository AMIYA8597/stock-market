"use client";

import { useEffect, useMemo, useState } from "react";
import { contractsApi, type DriftItem, type ModelAccuracyItem } from "@/lib/contracts-api";

function pct(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

export default function ModelPerformancePage(): JSX.Element {
  const [accuracy, setAccuracy] = useState<ModelAccuracyItem[]>([]);
  const [drift, setDrift] = useState<DriftItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);
      const [accRes, driftRes] = await Promise.allSettled([contractsApi.getModelAccuracy(), contractsApi.getDrift()]);

      if (!mounted) {
        return;
      }

      if (accRes.status === "fulfilled") {
        setAccuracy(accRes.value);
      } else {
        setError("Unable to load model accuracy contract.");
      }

      if (driftRes.status === "fulfilled") {
        setDrift(driftRes.value);
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

  const tableRows = useMemo(() => {
    return accuracy.map((item) => {
      const driftRow = drift.find((entry) => entry.model === item.model);
      return {
        model: item.model,
        directional_accuracy: item.directional_accuracy,
        p50_rmse: item.p50_rmse,
        winkler_coverage_score: item.winkler_coverage_score,
        ks_stat: driftRow?.ks_stat,
      };
    });
  }, [accuracy, drift]);

  const accuracyBars = useMemo(() => {
    return tableRows.map((row) => Math.max(8, Math.min(95, row.directional_accuracy * 100)));
  }, [tableRows]);

  const residualBars = useMemo(() => {
    return drift
      .flatMap((item) => item.residual_distribution.slice(0, 8))
      .slice(0, 24)
      .map((value) => Math.max(5, Math.min(90, Math.abs(value) * 100)));
  }, [drift]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-semibold">Model Performance</h2>
        <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1 text-xs text-[var(--nq-text-secondary)]">
          Updated: {lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : "--"}
        </div>
      </div>
      {error ? <p className="text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <div className="overflow-hidden rounded-lg border border-[var(--nq-border)] bg-[var(--nq-bg-card)]">
        <table className="w-full text-left text-sm">
          <thead className="bg-[var(--nq-bg-card-hover)] text-[var(--nq-text-secondary)]">
            <tr>
              <th className="px-4 py-2">Model</th>
              <th className="px-4 py-2">Directional Accuracy</th>
              <th className="px-4 py-2">P50 RMSE</th>
              <th className="px-4 py-2">Winkler Coverage</th>
              <th className="px-4 py-2">KS Stat</th>
            </tr>
          </thead>
          <tbody>
            {tableRows.map((row) => (
              <tr key={row.model} className="border-t border-[var(--nq-border)]">
                <td className="px-4 py-2 uppercase">{row.model}</td>
                <td className="px-4 py-2">{pct(row.directional_accuracy)}</td>
                <td className="px-4 py-2">{row.p50_rmse.toFixed(4)}</td>
                <td className="px-4 py-2">{row.winkler_coverage_score.toFixed(4)}</td>
                <td className="px-4 py-2">{typeof row.ks_stat === "number" ? row.ks_stat.toFixed(4) : "--"}</td>
              </tr>
            ))}
            {!loading && tableRows.length === 0 ? (
              <tr className="border-t border-[var(--nq-border)]">
                <td className="px-4 py-3 text-[var(--nq-text-secondary)]" colSpan={5}>No model performance data returned.</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h3 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Directional Accuracy Snapshot</h3>
          <div className="h-36 rounded bg-[rgba(255,255,255,0.03)] p-2">
            <div className="flex h-full items-end gap-[2px]">
              {(loading ? Array.from({ length: 30 }, () => 20) : accuracyBars).map((height, index) => (
                <div key={`acc-${index}`} className="w-full rounded-sm bg-[var(--nq-accent-cyan)]/52" style={{ height: `${height}%` }} />
              ))}
            </div>
          </div>
        </div>

        <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h3 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Residual Distribution Snapshot</h3>
          <div className="h-36 rounded bg-[rgba(255,255,255,0.03)] p-2">
            <div className="flex h-full items-end gap-[3px]">
              {(loading ? Array.from({ length: 24 }, () => 14) : residualBars).map((height, index) => (
                <div key={`res-${index}`} className="w-full rounded-sm bg-[var(--nq-accent-purple)]/55" style={{ height: `${height}%` }} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
