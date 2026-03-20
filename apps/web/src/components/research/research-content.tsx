"use client";

import { Card, CardHeader, CardTitle, Badge, RegimeBadge } from "@neuroquant/ui";

const MODEL_LEADERBOARD = [
  { name: "AMSTAN", ic: 0.082, directional: 72.4, sharpe: 1.84, bestSector: "Banking" },
  { name: "XGBoost Ensemble", ic: 0.071, directional: 68.1, sharpe: 1.52, bestSector: "IT" },
  { name: "LightGBM", ic: 0.068, directional: 67.3, sharpe: 1.48, bestSector: "Energy" },
  { name: "CatBoost", ic: 0.065, directional: 66.8, sharpe: 1.41, bestSector: "FMCG" },
  { name: "LSTM", ic: 0.058, directional: 64.2, sharpe: 1.28, bestSector: "Auto" },
  { name: "PPO Agent", ic: 0.054, directional: 62.8, sharpe: 1.18, bestSector: "Banking" },
];

const FACTORS = [
  { name: "Market (MKT)", beta: 0.87, contribution: 62, color: "#00D4FF" },
  { name: "Size (SMB)", beta: -0.12, contribution: 8, color: "#00E676" },
  { name: "Value (HML)", beta: 0.24, contribution: 14, color: "#FFB800" },
  { name: "Profitability (RMW)", beta: 0.18, contribution: 10, color: "#FF3B3B" },
  { name: "Investment (CMA)", beta: -0.08, contribution: 6, color: "#566176" },
];

export function ResearchContent() {
  return (
    <div className="space-y-6">
      <h1 className="font-display text-xl font-bold text-nq-text-primary">AI Research Hub</h1>

      <div className="grid grid-cols-12 gap-4">
        {/* Model leaderboard */}
        <Card noPadding className="col-span-12 lg:col-span-8">
          <CardHeader className="px-4 pt-3">
            <CardTitle>Model Performance Leaderboard</CardTitle>
            <Badge variant="accent">30-Day</Badge>
          </CardHeader>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-nq-border bg-nq-bg-elevated/50">
                {["#", "Model", "IC", "Dir. Acc%", "Sharpe", "Best Sector"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left text-[10px] font-medium text-nq-text-tertiary uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-nq-border">
              {MODEL_LEADERBOARD.map((m, i) => (
                <tr key={m.name} className="hover:bg-nq-bg-card/50">
                  <td className="px-4 py-2.5 font-mono text-nq-text-tertiary">{i + 1}</td>
                  <td className="px-4 py-2.5 font-semibold text-nq-text-primary">{m.name}</td>
                  <td className="px-4 py-2.5 font-mono text-nq-accent">{m.ic.toFixed(3)}</td>
                  <td className="px-4 py-2.5 font-mono text-nq-bull">{m.directional}%</td>
                  <td className="px-4 py-2.5 font-mono text-nq-text-primary">{m.sharpe.toFixed(2)}</td>
                  <td className="px-4 py-2.5"><Badge>{m.bestSector}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        {/* Regime Analysis */}
        <div className="col-span-12 lg:col-span-4 space-y-4">
          <Card>
            <CardHeader><CardTitle>Current Regime</CardTitle></CardHeader>
            <div className="flex items-center justify-center py-2">
              <RegimeBadge regime="bull" confidence={72} />
            </div>
            <div className="space-y-2 mt-3">
              <div className="text-[10px] text-nq-text-tertiary uppercase tracking-wider">Regime History (30d)</div>
              <div className="flex h-3 rounded-full overflow-hidden">
                <div className="bg-nq-bull/70" style={{ width: "65%" }} />
                <div className="bg-nq-warning/70" style={{ width: "20%" }} />
                <div className="bg-nq-bear/70" style={{ width: "15%" }} />
              </div>
              <div className="flex justify-between text-[10px] text-nq-text-tertiary">
                <span>Bull: 65%</span><span>Sideways: 20%</span><span>Bear: 15%</span>
              </div>
            </div>
            <div className="mt-3 space-y-1 border-t border-nq-border pt-3">
              <div className="text-[10px] text-nq-text-tertiary uppercase tracking-wider">Transition Probabilities</div>
              <div className="grid grid-cols-3 gap-1 text-center font-mono text-[10px]">
                <div /><div className="text-nq-bull">Bull</div><div className="text-nq-bear">Bear</div>
                <div className="text-nq-bull text-left">Bull</div><div className="text-nq-text-primary">0.82</div><div className="text-nq-text-secondary">0.18</div>
                <div className="text-nq-bear text-left">Bear</div><div className="text-nq-text-secondary">0.35</div><div className="text-nq-text-primary">0.65</div>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader><CardTitle>Factor Exposure</CardTitle></CardHeader>
            <div className="space-y-2">
              {FACTORS.map((f) => (
                <div key={f.name} className="flex items-center gap-2">
                  <span className="w-28 text-[10px] text-nq-text-secondary truncate">{f.name}</span>
                  <div className="flex-1 h-1.5 rounded-full bg-nq-bg-elevated overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${f.contribution}%`, backgroundColor: f.color }} />
                  </div>
                  <span className="font-mono text-[10px] text-nq-text-tertiary w-8 text-right">
                    {f.beta >= 0 ? "+" : ""}{f.beta.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
