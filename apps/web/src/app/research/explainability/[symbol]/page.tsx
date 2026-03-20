"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  contractsApi,
  type CounterfactualResponse,
  type ExplainAttentionResponse,
  type ExplainShapResponse,
} from "@/lib/contracts-api";

export default function ExplainabilityPage(): JSX.Element {
  const params = useParams<{ symbol: string }>();
  const symbol = decodeURIComponent(params?.symbol ?? "UNKNOWN").toUpperCase();

  const [shap, setShap] = useState<ExplainShapResponse | null>(null);
  const [attention, setAttention] = useState<ExplainAttentionResponse | null>(null);
  const [counterfactuals, setCounterfactuals] = useState<CounterfactualResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);

      const [shapRes, attentionRes, cfRes] = await Promise.allSettled([
        contractsApi.getExplainShap(symbol),
        contractsApi.getExplainAttention(symbol, "tft"),
        contractsApi.getCounterfactuals(symbol, { target_direction: "BUY", num_cfs: 3 }),
      ]);

      if (!mounted) {
        return;
      }

      if (shapRes.status === "fulfilled") {
        setShap(shapRes.value);
      } else {
        setError("Unable to load SHAP contract.");
      }

      if (attentionRes.status === "fulfilled") {
        setAttention(attentionRes.value);
      }

      if (cfRes.status === "fulfilled") {
        setCounterfactuals(cfRes.value);
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
  }, [symbol]);

  const shapRows = useMemo(() => {
    return shap?.feature_contributions ?? [];
  }, [shap]);

  const attentionGrid = useMemo(() => {
    return (attention?.weights ?? []).slice(0, 8).flatMap((row, headIndex) => row.slice(0, 20).map((value, stepIndex) => ({ headIndex, stepIndex, value })));
  }, [attention?.weights]);

  const rollingImportance = useMemo(() => {
    return shapRows
      .map((row) => ({
        name: row.name,
        strength: Math.max(8, Math.min(100, Math.round(Math.abs(row.shap_val) * 220))),
      }))
      .slice(0, 8);
  }, [shapRows]);

  return (
    <motion.main
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="min-h-screen bg-[var(--nq-bg-base)] p-4 text-[var(--nq-text-primary)] sm:p-6"
    >
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Explainability {symbol}</h1>
        <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1 text-xs text-[var(--nq-text-secondary)]">
          Model: {attention?.model ?? "tft"} | Updated: {lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : "--"}
        </div>
      </div>

      {error ? <p className="mb-3 text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <div className="space-y-4">
        <section className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">SHAP Waterfall</h2>
          <div className="space-y-2 text-xs">
            {(loading ? [] : shapRows).map((row) => {
              const width = Math.round(Math.min(240, Math.abs(row.shap_val) * 400));
              const positive = row.shap_val >= 0;
              return (
                <div key={row.name} className="grid grid-cols-[170px_1fr_80px] items-center gap-3">
                  <span className="text-[var(--nq-text-secondary)]">{row.name}</span>
                  <div className="relative h-6 rounded bg-[rgba(255,255,255,0.03)]">
                    <div
                      className="absolute top-0 h-full rounded"
                      style={{
                        width: `${width}px`,
                        left: positive ? "50%" : `calc(50% - ${width}px)`,
                        background: positive ? "rgba(0,230,118,0.45)" : "rgba(255,59,92,0.45)",
                      }}
                    />
                    <div className="absolute inset-y-0 left-1/2 w-px bg-[var(--nq-border)]" />
                  </div>
                  <span className="text-right">{row.feature_val.toFixed(3)}</span>
                </div>
              );
            })}
            {!loading && shapRows.length === 0 ? <p className="text-[var(--nq-text-secondary)]">No SHAP rows returned.</p> : null}
          </div>
        </section>

        <section className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Attention Heatmap (Heads x Timesteps)</h2>
          <div className="grid grid-cols-20 gap-[3px]">
            {(loading
              ? Array.from({ length: 160 }, (_, i) => ({ headIndex: Math.floor(i / 20), stepIndex: i % 20, value: 0.02 }))
              : attentionGrid
            ).map((cell) => {
              const alpha = 0.08 + Math.min(0.85, cell.value * 8);
              return (
                <div
                  key={`cell-${cell.headIndex}-${cell.stepIndex}`}
                  className="h-6 rounded"
                  style={{ background: `rgba(255,184,0,${alpha})` }}
                  title={`Head ${cell.headIndex + 1}, T-${20 - cell.stepIndex}`}
                />
              );
            })}
          </div>
        </section>

        <section className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Counterfactuals To Flip Signal</h2>
          <div className="grid grid-cols-1 gap-3 xl:grid-cols-3">
            {(loading ? [] : counterfactuals).map((cf) => (
              <article key={cf.cf_id} className="rounded border border-[var(--nq-border)] p-3">
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-sm font-semibold">{cf.cf_id}</span>
                  <span className="text-xs text-[var(--nq-text-secondary)]">{cf.resulting_signal}</span>
                </div>
                <div className="space-y-2 text-xs">
                  {cf.changed_features.map((item) => (
                    <div key={`${cf.cf_id}-${item.name}`} className="rounded bg-[rgba(255,255,255,0.02)] px-2 py-1">
                      <div className="font-medium">{item.name}</div>
                      <div className="text-[var(--nq-text-secondary)]">
                        {item.original.toFixed(4)} to {item.counterfactual.toFixed(4)}
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            ))}
            {!loading && counterfactuals.length === 0 ? <p className="text-xs text-[var(--nq-text-secondary)]">No counterfactuals returned.</p> : null}
          </div>
        </section>

        <section className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Rolling Feature Importance</h2>
          <div className="space-y-2 text-xs">
            {(loading ? [] : rollingImportance).map((row) => (
              <div key={row.name} className="grid grid-cols-[170px_1fr_48px] items-center gap-3">
                <span className="text-[var(--nq-text-secondary)]">{row.name}</span>
                <div className="h-3 rounded bg-[rgba(255,255,255,0.06)]">
                  <div className="h-full rounded bg-[var(--nq-accent-purple)]" style={{ width: `${row.strength}%` }} />
                </div>
                <span className="text-right">{row.strength}%</span>
              </div>
            ))}
            {!loading && rollingImportance.length === 0 ? <p className="text-[var(--nq-text-secondary)]">No importance series available.</p> : null}
          </div>
        </section>
      </div>
    </motion.main>
  );
}
