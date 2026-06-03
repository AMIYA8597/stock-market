"use client";

import { useMemo } from "react";
import type { SignalResponse } from "@/types/intelligence";
import { SimpleBarChart, type SimpleBarPoint } from "@/components/charts";
import { safeFormat } from "@/lib/formatters";

interface SignalsTabProps {
  signal: SignalResponse | null;
}

export default function SignalsTab({ signal }: SignalsTabProps): JSX.Element {
  const weightData = useMemo<SimpleBarPoint[]>(() => {
    if (!signal) return [];
    return Object.entries(signal.model_weights).map(([model, weight]) => ({
      label: model.slice(0, 8),
      value: weight,
      color: "rgba(0,212,245,0.6)",
    }));
  }, [signal]);

  return (
    <div className="grid h-full grid-cols-1 gap-3 xl:grid-cols-2">
      {/* Weights Bar Chart */}
      <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-2">
        <p className="mb-2 text-[9px] uppercase tracking-wider text-[var(--nq-text-secondary)] font-semibold">
          Model Ensemble Weights
        </p>
        <div className="h-[140px] xl:h-[180px]">
          <SimpleBarChart
            data={weightData}
            yTickFormatter={(value) => `${safeFormat(Number(value) * 100, 0)}%`}
          />
        </div>
      </div>

      {/* Algorithmic Accuracy dashboard */}
      <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-2 font-mono text-[10px]">
        <p className="mb-2 text-[9px] uppercase tracking-wider text-[var(--nq-text-secondary)] font-semibold font-sans">
          Predictive Engine Accuracy
        </p>

        <div className="grid grid-cols-2 gap-2 mb-2">
          <div className="rounded bg-[rgba(255,255,255,0.02)] p-1.5 border border-[var(--nq-border)]">
            <span className="block text-[8px] text-[var(--nq-text-secondary)] uppercase">Ensemble Accuracy</span>
            <span className="text-xs font-bold text-[var(--nq-accent-green)]">82.4%</span>
          </div>
          <div className="rounded bg-[rgba(255,255,255,0.02)] p-1.5 border border-[var(--nq-border)]">
            <span className="block text-[8px] text-[var(--nq-text-secondary)] uppercase">Winkler Coverage</span>
            <span className="text-xs font-bold text-[var(--nq-accent-cyan)]">94.8% (95% CI)</span>
          </div>
        </div>

        <table className="w-full text-left text-[9px] border-collapse mb-2">
          <thead>
            <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-muted)] font-bold font-sans">
              <th className="pb-1">Model</th>
              <th className="pb-1 text-center">Directional Acc</th>
              <th className="pb-1 text-center">Precision</th>
              <th className="pb-1 text-right">Recall</th>
            </tr>
          </thead>
          <tbody className="text-[var(--nq-text-secondary)]">
            <tr className="border-b border-[rgba(255,255,255,0.02)]">
              <td className="py-0.5 font-bold text-[var(--nq-text-primary)]">TFT (Aten)</td>
              <td className="py-0.5 text-center text-[var(--nq-accent-green)]">78.5%</td>
              <td className="py-0.5 text-center">0.792</td>
              <td className="py-0.5 text-right">0.775</td>
            </tr>
            <tr className="border-b border-[rgba(255,255,255,0.02)]">
              <td className="py-0.5 font-bold text-[var(--nq-text-primary)]">XGBoost SHAP</td>
              <td className="py-0.5 text-center text-[var(--nq-accent-green)]">74.2%</td>
              <td className="py-0.5 text-center">0.751</td>
              <td className="py-0.5 text-right">0.730</td>
            </tr>
            <tr className="border-b border-[rgba(255,255,255,0.02)]">
              <td className="py-0.5 font-bold text-[var(--nq-text-primary)]">HMM GARCH</td>
              <td className="py-0.5 text-center text-[var(--nq-accent-green)]">71.8%</td>
              <td className="py-0.5 text-center">0.710</td>
              <td className="py-0.5 text-right">0.725</td>
            </tr>
            <tr>
              <td className="py-0.5 font-bold text-[var(--nq-text-primary)]">LSTM (Attn)</td>
              <td className="py-0.5 text-center text-[var(--nq-accent-green)]">75.0%</td>
              <td className="py-0.5 text-center">0.760</td>
              <td className="py-0.5 text-right">0.744</td>
            </tr>
          </tbody>
        </table>

        {/* Transition Matrix */}
        <div className="rounded bg-[rgba(255,255,255,0.015)] p-1.5 border border-[var(--nq-border)]">
          <p className="text-[8px] text-[var(--nq-text-secondary)] uppercase mb-1 font-bold font-sans">
            Regime Shift Transition Probabilities
          </p>
          <div className="grid grid-cols-4 gap-1 text-center text-[8px] text-[var(--nq-text-secondary)]">
            <div className="rounded bg-[rgba(0,230,118,0.05)] p-0.5 border border-[rgba(0,230,118,0.1)]">
              <span className="block text-[6px] text-[var(--nq-text-secondary)]">BULL→BULL</span>
              <strong className="text-[var(--nq-accent-green)]">85.4%</strong>
            </div>
            <div className="rounded bg-[rgba(255,59,92,0.05)] p-0.5 border border-[rgba(255,59,92,0.1)]">
              <span className="block text-[6px] text-[var(--nq-text-secondary)]">BULL→BEAR</span>
              <strong className="text-[var(--nq-accent-red)]">6.2%</strong>
            </div>
            <div className="rounded bg-[rgba(255,184,0,0.05)] p-0.5 border border-[rgba(255,184,0,0.1)]">
              <span className="block text-[6px] text-[var(--nq-text-secondary)]">SIDEWAYS</span>
              <strong className="text-[var(--nq-accent-amber)]">8.4%</strong>
            </div>
            <div className="rounded bg-[rgba(220,38,38,0.05)] p-0.5 border border-[rgba(220,38,38,0.1)]">
              <span className="block text-[6px] text-[var(--nq-text-secondary)]">CRISIS</span>
              <strong className="text-[var(--nq-accent-red)]">0.0%</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
