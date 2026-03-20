"use client";

import type { SignalResponse } from "@/types/intelligence";

interface SignalPanelProps {
  signal: SignalResponse | null;
}

const badgeStyles: Record<string, string> = {
  STRONG_BUY: "bg-[rgba(0,230,118,0.18)] text-[#00E676] border-[#00E676]",
  BUY: "bg-[rgba(0,230,118,0.12)] text-[#00E676] border-[#00E676]",
  NEUTRAL: "bg-[rgba(255,184,0,0.12)] text-[#FFB800] border-[#FFB800]",
  SELL: "bg-[rgba(255,59,92,0.12)] text-[#FF3B5C] border-[#FF3B5C]",
  STRONG_SELL: "bg-[rgba(255,59,92,0.18)] text-[#FF3B5C] border-[#FF3B5C]",
};

export default function SignalPanel({ signal }: SignalPanelProps): JSX.Element {
  const direction = signal?.ensemble.direction ?? "NEUTRAL";
  const confidence = signal ? (signal.ensemble.confidence * 100).toFixed(1) : "0.0";
  const featureRows = (signal?.models.xgboost.top_features ?? []).slice(0, 5);

  return (
    <aside className="border-t border-[var(--nq-border)] bg-[var(--nq-bg-secondary)] p-3 lg:border-l lg:border-t-0">
      <div className="mb-3 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Ensemble signal</p>
        <span className={`inline-flex rounded border px-2 py-1 text-xs font-semibold ${badgeStyles[direction]}`}>
          {direction}
        </span>
        <div className="mt-2 grid grid-cols-2 gap-2 text-xs sm:text-sm">
          <p className="rounded bg-[rgba(255,255,255,0.03)] px-2 py-1 text-[var(--nq-text-secondary)]">Confidence {confidence}%</p>
          <p className="rounded bg-[rgba(255,255,255,0.03)] px-2 py-1 text-[var(--nq-text-secondary)]">Regime {signal?.regime.state ?? "-"}</p>
        </div>
        <p className="mt-2 text-sm text-[var(--nq-text-secondary)]">
          Kelly {(signal?.ensemble.kelly_fraction ?? 0).toFixed(3)}
        </p>
      </div>

      <div className="mb-3 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Model details</p>
        <div className="grid grid-cols-2 gap-2 text-xs text-[var(--nq-text-secondary)]">
          <div className="rounded border border-[var(--nq-border)] px-2 py-1">TFT p50 {(signal?.models.tft.p50 ?? 0).toFixed(4)}</div>
          <div className="rounded border border-[var(--nq-border)] px-2 py-1">HMM {signal?.models.hmm_garch.regime_signal ?? "-"}</div>
          <div className="rounded border border-[var(--nq-border)] px-2 py-1">GNN {(signal?.models.gnn.spillover_risk ?? 0).toFixed(3)}</div>
          <div className="rounded border border-[var(--nq-border)] px-2 py-1">LSTM {(signal?.models.lstm_attn.raw_signal ?? 0).toFixed(3)}</div>
        </div>
      </div>

      <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">XGBoost top features</p>
        <div className="space-y-1 text-xs text-[var(--nq-text-secondary)]">
          {featureRows.map((feature) => (
            <div key={String(feature.name)} className="flex justify-between">
              <span>{String(feature.name)}</span>
              <span>{Number(feature.shap_value).toFixed(4)}</span>
            </div>
          ))}
          {featureRows.length === 0 ? <div className="rounded bg-[rgba(255,255,255,0.03)] px-2 py-1">No feature attribution received yet.</div> : null}
        </div>
      </div>
    </aside>
  );
}
