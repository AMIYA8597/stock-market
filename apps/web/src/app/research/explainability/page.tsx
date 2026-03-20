"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { contractsApi, type ExplainShapResponse } from "@/lib/contracts-api";

const symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"];

export default function ExplainabilityIndexPage(): JSX.Element {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [summaries, setSummaries] = useState<Record<string, ExplainShapResponse>>({});

  useEffect(() => {
    let mounted = true;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);

      const requests = await Promise.allSettled(symbols.map((symbol) => contractsApi.getExplainShap(symbol)));
      if (!mounted) {
        return;
      }

      const next: Record<string, ExplainShapResponse> = {};
      let hasError = false;

      requests.forEach((result, index) => {
        const symbol = symbols[index];
        if (!symbol) {
          return;
        }
        if (result.status === "fulfilled") {
          next[symbol] = result.value;
        } else {
          hasError = true;
        }
      });

      setSummaries(next);
      if (hasError) {
        setError("Some explainability contracts failed to load.");
      }
      setLoading(false);
    }

    void load();

    return () => {
      mounted = false;
    };
  }, []);

  const topDriver = useMemo(() => {
    const firstSymbol = symbols.find((symbol) => summaries[symbol]);
    if (!firstSymbol) {
      return "--";
    }
    const summary = summaries[firstSymbol];
    if (!summary) {
      return "--";
    }
    const features = summary.feature_contributions;
    if (features.length === 0) {
      return "--";
    }
    const best = [...features].sort((a, b) => Math.abs(b.shap_val) - Math.abs(a.shap_val))[0];
    return best?.name ?? "--";
  }, [summaries]);

  const avgOutputSignal = useMemo(() => {
    const values = Object.values(summaries).map((item) => item.output_value);
    if (values.length === 0) {
      return "--";
    }
    const avg = values.reduce((sum, value) => sum + value, 0) / values.length;
    return avg.toFixed(3);
  }, [summaries]);

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Explainability</h2>
      <p className="text-sm text-[var(--nq-text-secondary)]">Inspect SHAP, attention, and counterfactual outputs per symbol.</p>
      {error ? <p className="text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <div className="grid gap-3 sm:grid-cols-3">
        {[
          ["Top Driver", loading ? "..." : topDriver],
          ["Symbols Loaded", loading ? "..." : `${Object.keys(summaries).length}/${symbols.length}`],
          ["Average Output", loading ? "..." : avgOutputSignal],
        ].map(([k, v]) => (
          <div key={k} className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3">
            <div className="text-xs text-[var(--nq-text-secondary)]">{k}</div>
            <div className="mt-1 text-sm font-semibold">{v}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {symbols.map((symbol) => {
          const shap = summaries[symbol];
          const bestFeature = shap?.feature_contributions
            ? [...shap.feature_contributions].sort((a, b) => Math.abs(b.shap_val) - Math.abs(a.shap_val))[0]?.name
            : undefined;

          return (
            <Link
              key={symbol}
              href={`/research/explainability/${symbol}`}
              className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3 text-sm transition-colors hover:border-[var(--nq-accent-cyan)]"
            >
              <div className="font-medium">{symbol}</div>
              <div className="mt-1 text-xs text-[var(--nq-text-secondary)]">Top feature: {loading ? "..." : (bestFeature ?? "--")}</div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
