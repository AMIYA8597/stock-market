"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { contractsApi, type DriftItem, type EnsembleWeightPoint, type ModelAccuracyItem } from "@/lib/contracts-api";

function formatRatio(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return value.toFixed(3);
}

export default function ModelMonitorPage(): JSX.Element {
  const [accuracy, setAccuracy] = useState<ModelAccuracyItem[]>([]);
  const [drift, setDrift] = useState<DriftItem[]>([]);
  const [weights, setWeights] = useState<EnsembleWeightPoint[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);
      const [accuracyRes, driftRes, weightsRes] = await Promise.allSettled([
        contractsApi.getModelAccuracy(),
        contractsApi.getDrift(),
        contractsApi.getEnsembleWeightHistory(120),
      ]);

      if (!mounted) {
        return;
      }

      if (accuracyRes.status === "fulfilled") {
        setAccuracy(accuracyRes.value);
      } else {
        setError("Unable to load model accuracy contract.");
      }

      if (driftRes.status === "fulfilled") {
        setDrift(driftRes.value);
      }

      if (weightsRes.status === "fulfilled") {
        setWeights(weightsRes.value);
      }

      setLastUpdated(new Date().toISOString());

      setLoading(false);
    }

    void load();

    const timer = setInterval(() => {
      void load();
    }, 30_000);

    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  const tft = useMemo(() => accuracy.find((item) => item.model === "tft") ?? null, [accuracy]);
  const ensemble = useMemo(() => accuracy.find((item) => item.model === "ensemble") ?? null, [accuracy]);

  const weightColumns = useMemo(() => {
    const data = weights.slice(-30);
    if (data.length === 0) {
      return [] as EnsembleWeightPoint[];
    }
    return data;
  }, [weights]);

  const modelBars = useMemo(() => {
    return accuracy.map((item) => ({
      model: item.model,
      accuracy: item.directional_accuracy,
    }));
  }, [accuracy]);

  return (
    <motion.main
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, ease: "easeOut" }}
      className="min-h-screen bg-[var(--nq-bg-base)] p-4 text-[var(--nq-text-primary)] sm:p-6"
    >
      <h1 className="mb-2 text-2xl font-semibold">Model Monitor</h1>
      <p className="mb-4 text-xs text-[var(--nq-text-secondary)]">
        Live contracts: model accuracy, drift, and ensemble weight history. Updated: {lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : "--"}
      </p>
      {error ? <p className="mb-2 text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["TFT 21d Accuracy", formatRatio(tft?.directional_accuracy)],
          ["Ensemble 21d Accuracy", formatRatio(ensemble?.directional_accuracy)],
          ["P50 RMSE", formatRatio(ensemble?.p50_rmse ?? tft?.p50_rmse)],
          ["Winkler Coverage", formatRatio(ensemble?.winkler_coverage_score)],
        ].map(([key, value]) => (
          <div key={key} className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3">
            <div className="text-xs text-[var(--nq-text-secondary)]">{key}</div>
            <div className="mt-1 text-sm font-semibold">{loading ? "..." : value}</div>
          </div>
        ))}
      </section>

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Ensemble Weight Evolution</h2>
          <div className="h-40 rounded bg-[rgba(255,255,255,0.03)] p-2">
            <div className="grid h-full grid-cols-5 gap-1">
              {["tft", "hmm_garch", "gnn", "lstm_attn", "xgboost"].map((modelKey) => (
                <div key={modelKey} className="flex h-full flex-col justify-end gap-[2px]">
                  {(weightColumns.length === 0 ? Array.from({ length: 20 }, () => 20) : weightColumns.map((point) => point[modelKey as keyof EnsembleWeightPoint] as number)).map((weightValue, index) => (
                    <div key={`${modelKey}-${index}`} className="w-full rounded-sm bg-[var(--nq-accent-cyan)]/42" style={{ height: `${Math.max(6, weightValue * 100)}%` }} />
                  ))}
                </div>
              ))}
            </div>
          </div>
        </article>

        <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Model Accuracy Grid</h2>
          <div className="h-40 rounded bg-[rgba(255,255,255,0.03)] p-2">
            <div className="flex h-full items-end gap-2">
              {(modelBars.length === 0 ? Array.from({ length: 6 }, () => ({ model: "--", accuracy: 0.15 })) : modelBars).map((bar, index) => (
                <div key={`${bar.model}-${index}`} className="flex h-full w-full flex-col items-center justify-end gap-2">
                  <div className="w-full rounded-sm bg-[var(--nq-accent-green)]/55" style={{ height: `${Math.max(10, bar.accuracy * 100)}%` }} />
                  <span className="text-[10px] text-[var(--nq-text-secondary)]">{bar.model}</span>
                </div>
              ))}
            </div>
          </div>
        </article>

        <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Drift Detection</h2>
          <table className="min-w-full text-xs">
            <thead>
              <tr className="text-[var(--nq-text-secondary)]">
                <th className="pb-2 text-left font-medium">Model</th>
                <th className="pb-2 text-right font-medium">ADWIN p</th>
                <th className="pb-2 text-right font-medium">Drift</th>
              </tr>
            </thead>
            <tbody>
              {drift.map((row) => (
                <tr key={row.model} className="border-t border-[var(--nq-border)]">
                  <td className="py-2">{row.model}</td>
                  <td className="py-2 text-right">{row.adwin_p_value.toFixed(3)}</td>
                  <td className="py-2 text-right">{row.drift_detected ? "YES" : "NO"}</td>
                </tr>
              ))}
              {!loading && drift.length === 0 ? (
                <tr>
                  <td className="py-2 text-[var(--nq-text-secondary)]" colSpan={3}>No drift data returned by monitor contract.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </article>

        <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Residual Distribution</h2>
          <div className="h-40 rounded bg-[rgba(255,255,255,0.03)] p-2">
            <div className="flex h-full items-end gap-[3px]">
              {(drift[0]?.residual_distribution ?? Array.from({ length: 20 }, () => 0.1)).slice(0, 24).map((value, index) => {
                const normalized = Math.min(100, Math.max(5, Math.abs(value) * 100));
                return <div key={`hist-${index}`} className="w-full rounded-sm bg-[var(--nq-accent-purple)]/52" style={{ height: `${normalized}%` }} />;
              })}
            </div>
          </div>
          <p className="mt-2 text-xs text-[var(--nq-text-secondary)]">Active drift flags: {drift.filter((item) => item.drift_detected).length}</p>
        </article>
      </div>
    </motion.main>
  );
}
