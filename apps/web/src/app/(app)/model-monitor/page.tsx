"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/dashboard/premium";
import { contractsApi, type DriftItem, type EnsembleWeightPoint, type ModelAccuracyItem } from "@/lib/contracts-api";
import { ChartCard, SimpleBarChart, type SimpleBarPoint, SimpleLineAreaChart, type LineAreaPoint } from "@/components/charts";

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
  const [loading, setLoading] = useState(true);
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

    const timer = window.setInterval(() => {
      void load();
    }, 30_000);

    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);

  const tft = useMemo(() => accuracy.find((item) => item.model === "tft") ?? null, [accuracy]);
  const ensemble = useMemo(() => accuracy.find((item) => item.model === "ensemble") ?? null, [accuracy]);
  const weightColumns = useMemo(() => weights.slice(-30), [weights]);

  const accuracyBarData = useMemo<SimpleBarPoint[]>(() => {
    if (accuracy.length === 0) {
      return [
        { label: "tft", value: 0.15, color: "rgba(0,230,118,0.55)" },
        { label: "lstm", value: 0.13, color: "rgba(0,212,245,0.55)" },
        { label: "xgb", value: 0.12, color: "rgba(139,92,246,0.55)" },
      ];
    }

    return accuracy.map((item) => ({
      label: item.model,
      value: item.directional_accuracy,
      color: "rgba(0,230,118,0.55)",
    }));
  }, [accuracy]);

  const tftWeightTrend = useMemo<LineAreaPoint[]>(() => {
    if (weightColumns.length === 0) {
      return Array.from({ length: 24 }, (_, idx) => ({ label: String(idx + 1), value: 0.2 }));
    }

    return weightColumns.map((point, idx) => ({
      label: String(idx + 1),
      value: point.tft,
    }));
  }, [weightColumns]);

  const residualDistributionBars = useMemo<SimpleBarPoint[]>(() => {
    const residuals = drift[0]?.residual_distribution ?? Array.from({ length: 20 }, () => 0.1);
    return residuals.slice(0, 24).map((value, idx) => ({
      label: String(idx + 1),
      value: Math.abs(value),
      color: "rgba(139,92,246,0.55)",
    }));
  }, [drift]);

  const modelHealthStatus = useMemo(() => {
    return accuracy.map((item) => {
      const driftStatus = drift.find((d) => d.model === item.model);
      const isDrifting = driftStatus?.drift_detected ?? false;
      const accuracyPct = item.directional_accuracy;

      let status: "healthy" | "warning" | "critical";
      if (isDrifting) {
        status = "critical";
      } else if (accuracyPct < 0.5) {
        status = "warning";
      } else {
        status = "healthy";
      }

      return {
        model: item.model,
        status,
        accuracy: accuracyPct,
        isDrifting,
      };
    });
  }, [accuracy, drift]);

  const ensembleStability = useMemo(() => {
    if (weightColumns.length < 2) {
      return 0.85;
    }

    const values = weightColumns.map((w) => w.tft);
    const mean = values.reduce((a, b) => a + b, 0) / values.length;
    const variance = values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / values.length;
    const stdDev = Math.sqrt(variance);
    const cv = stdDev / mean;
    return Math.max(0, 1 - cv);
  }, [weightColumns]);

  const driftAlertCount = useMemo(() => drift.filter((d) => d.drift_detected).length, [drift]);

  return (
    <motion.main
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, ease: "easeOut" }}
      className="min-h-screen bg-[radial-gradient(1000px_500px_at_0%_0%,rgba(0,212,245,0.12),transparent_45%),radial-gradient(900px_420px_at_100%_0%,rgba(139,92,246,0.10),transparent_45%),var(--nq-bg-base)] p-4 text-[var(--nq-text-primary)] sm:p-6"
    >
      <section className="mb-6 rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-5 shadow-[0_18px_48px_rgba(0,0,0,0.22)]">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="bull" className="px-3 py-1.5 text-[10px] uppercase tracking-[0.16em]">Model monitor</Badge>
              <Badge variant="outline" className="px-3 py-1.5 text-[10px] uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">Rolling 21d health</Badge>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-[var(--nq-text-primary)] sm:text-4xl">Model health dashboard with drift and ensemble stability in view.</h1>
            <p className="text-sm text-[var(--nq-text-secondary)]">Live contracts: accuracy, drift, and ensemble weight history. Updated: {lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : "--"}</p>
          </div>
          <Button variant="secondary" size="sm" onClick={() => window.location.reload()}>Refresh</Button>
        </div>
      </section>

      {error ? <p className="mb-2 text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["TFT 21d Accuracy", formatRatio(tft?.directional_accuracy)],
          ["Ensemble 21d Accuracy", formatRatio(ensemble?.directional_accuracy)],
          ["P50 RMSE", formatRatio(ensemble?.p50_rmse ?? tft?.p50_rmse)],
          ["Winkler Coverage", formatRatio(ensemble?.winkler_coverage_score)],
        ].map(([key, value]) => (
          <div key={key} className="rounded-[1.25rem] border border-white/10 bg-white/[0.04] px-4 py-3">
            <div className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">{key}</div>
            <div className="mt-2 text-sm font-semibold text-[var(--nq-text-primary)]">{loading ? "..." : value}</div>
          </div>
        ))}
      </section>

      {driftAlertCount > 0 ? (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-4 rounded border border-[var(--nq-accent-red)]/50 bg-[var(--nq-accent-red)]/10 px-4 py-3"
        >
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-[var(--nq-accent-red)]" style={{ animation: "pulse 2s infinite" }} />
            <div className="text-sm font-medium text-[var(--nq-accent-red)]">
              {driftAlertCount} model{driftAlertCount !== 1 ? "s" : ""} detected drift in this window. Monitor closely.
            </div>
          </div>
        </motion.div>
      ) : null}

      <div className="mt-4 rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-medium uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Ensemble Stability</h2>
            <p className="text-xs text-[var(--nq-text-secondary)]">Weight variance normalized coefficient</p>
          </div>
          <div className="text-right">
            <div className="text-lg font-semibold">{(ensembleStability * 100).toFixed(1)}%</div>
            <div className={`text-xs font-medium ${ensembleStability > 0.75 ? "text-[var(--nq-accent-green)]" : ensembleStability > 0.5 ? "text-[var(--nq-accent-amber)]" : "text-[var(--nq-accent-red)]"}`}>
              {ensembleStability > 0.75 ? "Stable" : ensembleStability > 0.5 ? "Moderate" : "Volatile"}
            </div>
          </div>
        </div>
        <div className="mt-3 h-2 rounded-full bg-[rgba(255,255,255,0.05)]">
          <div
            className={`h-full rounded-full transition-all duration-500 ${ensembleStability > 0.75 ? "bg-[var(--nq-accent-green)]" : ensembleStability > 0.5 ? "bg-[var(--nq-accent-amber)]" : "bg-[var(--nq-accent-red)]"}`}
            style={{ width: `${ensembleStability * 100}%` }}
          />
        </div>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {modelHealthStatus.map((item) => (
          <div
            key={item.model}
            className={`rounded-[1.25rem] border p-3 transition-all duration-300 ${item.status === "critical" ? "border-[var(--nq-accent-red)]/50 bg-[var(--nq-accent-red)]/10" : item.status === "warning" ? "border-[var(--nq-accent-amber)]/50 bg-[var(--nq-accent-amber)]/10" : "border-[var(--nq-border)] bg-[var(--nq-bg-card)]"}`}
          >
            <div className="mb-2 flex items-center justify-between">
              <div className="font-semibold text-[var(--nq-text-primary)]" style={{ textTransform: "uppercase", fontSize: "0.75rem" }}>
                {item.model}
              </div>
              <div className={`inline-block rounded-full px-2 py-1 text-[10px] font-bold ${item.status === "critical" ? "bg-[var(--nq-accent-red)]/30 text-[var(--nq-accent-red)]" : item.status === "warning" ? "bg-[var(--nq-accent-amber)]/30 text-[var(--nq-accent-amber)]" : "bg-[var(--nq-accent-green)]/30 text-[var(--nq-accent-green)]"}`}>
                {item.status.toUpperCase()}
              </div>
            </div>
            <div className="text-sm font-medium">{(item.accuracy * 100).toFixed(1)}%</div>
            {item.isDrifting ? <div className="mt-1 text-[10px] text-[var(--nq-accent-red)]">Drift Detected</div> : null}
          </div>
        ))}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <ChartCard title="Ensemble Weight Evolution" subtitle="TFT rolling weight (recent samples)">
          <div className="h-40 rounded-[1rem] bg-[rgba(255,255,255,0.03)] p-2">
            <SimpleLineAreaChart data={tftWeightTrend} mode="line" stroke="var(--nq-accent-cyan)" yTickFormatter={(value) => `${(value * 100).toFixed(0)}%`} />
          </div>
        </ChartCard>

        <ChartCard title="Model Accuracy Grid" subtitle="Directional accuracy by model">
          <div className="h-40 rounded-[1rem] bg-[rgba(255,255,255,0.03)] p-2">
            <SimpleBarChart data={accuracyBarData} yTickFormatter={(value) => `${(value * 100).toFixed(0)}%`} />
          </div>
        </ChartCard>

        <article className="rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-4">
          <h2 className="mb-3 text-sm font-medium uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Drift Detection</h2>
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

        <ChartCard title="Residual Distribution" subtitle="Absolute residual histogram">
          <div className="h-40 rounded-[1rem] bg-[rgba(255,255,255,0.03)] p-2">
            <SimpleBarChart data={residualDistributionBars} />
          </div>
          <p className="mt-2 text-xs text-[var(--nq-text-secondary)]">Active drift flags: {drift.filter((item) => item.drift_detected).length}</p>
        </ChartCard>
      </div>
    </motion.main>
  );
}