"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { contractsApi, type DriftItem, type ModelAccuracyItem, type RegimeCurrentResponse } from "@/lib/contracts-api";

const links = [
  { href: "/research/regime-analysis", label: "Regime Analysis" },
  { href: "/research/correlation-graph", label: "Correlation Graph" },
  { href: "/research/factor-exposure", label: "Factor Exposure" },
  { href: "/research/model-performance", label: "Model Performance" },
  { href: "/research/explainability/RELIANCE.NS", label: "Explainability" },
];

function pct(value: number | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return `${(value * 100).toFixed(2)}%`;
}

export default function ResearchHomePage(): JSX.Element {
  const [regime, setRegime] = useState<RegimeCurrentResponse | null>(null);
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
      const [regimeRes, accuracyRes, driftRes] = await Promise.allSettled([
        contractsApi.getRegimeCurrent(),
        contractsApi.getModelAccuracy(),
        contractsApi.getDrift(),
      ]);

      if (!mounted) {
        return;
      }

      if (regimeRes.status === "fulfilled") {
        setRegime(regimeRes.value);
      } else {
        setError("Unable to load regime contract.");
      }

      if (accuracyRes.status === "fulfilled") {
        setAccuracy(accuracyRes.value);
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

  const ensemble = useMemo(() => accuracy.find((item) => item.model === "ensemble") ?? null, [accuracy]);
  const activeDrifts = useMemo(() => drift.filter((item) => item.drift_detected).length, [drift]);

  const regimeConfidence = useMemo(() => {
    if (!regime) {
      return undefined;
    }
    return regime.probs[regime.state] ?? undefined;
  }, [regime]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-semibold">Research Workbench</h2>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setLoading(true);
              setError(null);
              void (async () => {
                const [regimeRes, accuracyRes, driftRes] = await Promise.allSettled([
                  contractsApi.getRegimeCurrent(),
                  contractsApi.getModelAccuracy(),
                  contractsApi.getDrift(),
                ]);

                if (regimeRes.status === "fulfilled") {
                  setRegime(regimeRes.value);
                }
                if (accuracyRes.status === "fulfilled") {
                  setAccuracy(accuracyRes.value);
                }
                if (driftRes.status === "fulfilled") {
                  setDrift(driftRes.value);
                }
                setLastUpdated(new Date().toISOString());
                setLoading(false);
              })();
            }}
            className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1 text-xs text-[var(--nq-text-secondary)] transition hover:border-[var(--nq-accent-cyan)]"
          >
            Refresh
          </button>
          <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1 text-xs text-[var(--nq-text-secondary)]">
            Horizon: 252d | Updated: {lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : "--"}
          </div>
        </div>
      </div>

      {error ? <p className="text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Current Regime", loading ? "..." : regime?.state ?? "--", "rgba(0,230,118,0.16)"],
          ["Regime Confidence", loading ? "..." : pct(regimeConfidence), "rgba(0,212,245,0.16)"],
          ["Ensemble Accuracy", loading ? "..." : pct(ensemble?.directional_accuracy), "rgba(139,92,246,0.16)"],
          ["Drift Alerts", loading ? "..." : `${activeDrifts} ACTIVE`, "rgba(255,184,0,0.16)"],
        ].map(([k, v, bg]) => (
          <div key={k} className="rounded border border-[var(--nq-border)] px-4 py-3" style={{ background: String(bg) }}>
            <div className="text-xs text-[var(--nq-text-secondary)]">{k}</div>
            <div className="mt-1 text-sm font-semibold">{v}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3 text-sm transition-colors hover:border-[var(--nq-accent-cyan)]"
          >
            <div className="font-medium">{link.label}</div>
            <div className="mt-1 text-xs text-[var(--nq-text-secondary)]">Open module and inspect latest model diagnostics.</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
