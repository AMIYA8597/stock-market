"use client";

import { cn, Badge, formatPrice, formatPercent, getPriceColor, getDirectionArrow } from "@neuroquant/ui";

interface AiForecastTabProps {
  symbol: string;
}

const MODEL_PREDICTIONS = [
  { name: "AMSTAN", prediction: 2912, direction: 1 as const, confidence: 78, weight: 0.35 },
  { name: "XGBoost", prediction: 2895, direction: 1 as const, confidence: 72, weight: 0.20 },
  { name: "LightGBM", prediction: 2880, direction: 1 as const, confidence: 68, weight: 0.20 },
  { name: "LSTM", prediction: 2870, direction: 1 as const, confidence: 65, weight: 0.15 },
  { name: "CatBoost", prediction: 2855, direction: 0 as const, confidence: 52, weight: 0.10 },
];

const FEATURE_IMPORTANCES = [
  { feature: "RSI(14)", importance: 0.142, direction: "bullish" as const },
  { feature: "MACD Signal", importance: 0.128, direction: "bullish" as const },
  { feature: "Volume Surge", importance: 0.098, direction: "bullish" as const },
  { feature: "Sector Momentum", importance: 0.087, direction: "bullish" as const },
  { feature: "VIX Level", importance: 0.076, direction: "neutral" as const },
  { feature: "BB Width", importance: 0.065, direction: "bearish" as const },
  { feature: "USD/INR", importance: 0.054, direction: "bearish" as const },
  { feature: "Yield Curve", importance: 0.048, direction: "neutral" as const },
];

function ConfidenceGauge({ value }: { value: number }) {
  const circumference = 2 * Math.PI * 38;
  const offset = circumference - (value / 100) * circumference;
  const color = value >= 70 ? "var(--nq-bull)" : value >= 50 ? "var(--nq-warning)" : "var(--nq-bear)";

  return (
    <div className="relative flex items-center justify-center">
      <svg width="100" height="100" className="-rotate-90">
        <circle cx="50" cy="50" r="38" fill="none" stroke="var(--nq-border)" strokeWidth="6" />
        <circle
          cx="50" cy="50" r="38" fill="none" stroke={color} strokeWidth="6"
          strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
          className="transition-all duration-1000"
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-mono text-xl font-bold" style={{ color }}>{value}%</span>
        <span className="text-[9px] text-nq-text-tertiary">Bullish</span>
      </div>
    </div>
  );
}

export function AiForecastTab({ symbol }: AiForecastTabProps) {
  return (
    <div className="space-y-4">
      {/* Direction confidence */}
      <div className="flex items-center justify-center">
        <ConfidenceGauge value={73} />
      </div>

      {/* Price targets */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: "5-Day", price: 2892, pct: 1.56 },
          { label: "10-Day", price: 2935, pct: 3.07 },
          { label: "30-Day", price: 3010, pct: 5.70 },
        ].map((target) => (
          <div key={target.label} className="rounded-nq bg-nq-bg-elevated p-2 text-center">
            <div className="text-[10px] text-nq-text-tertiary">{target.label}</div>
            <div className="font-mono text-sm font-semibold text-nq-text-primary">{formatPrice(target.price)}</div>
            <div className={cn("text-[10px] font-mono", getPriceColor(target.pct))}>
              {getDirectionArrow(target.pct)} {formatPercent(target.pct)}
            </div>
          </div>
        ))}
      </div>

      {/* Model ensemble */}
      <div>
        <h4 className="mb-2 text-[10px] font-medium text-nq-text-tertiary uppercase tracking-wider">Model Ensemble</h4>
        <div className="space-y-1.5">
          {MODEL_PREDICTIONS.map((m) => (
            <div key={m.name} className="flex items-center gap-2">
              <span className="w-16 text-xs text-nq-text-secondary truncate">{m.name}</span>
              <div className="flex-1 h-1.5 rounded-full bg-nq-bg-elevated overflow-hidden">
                <div
                  className={cn("h-full rounded-full transition-all", m.direction > 0 ? "bg-nq-bull" : m.direction < 0 ? "bg-nq-bear" : "bg-nq-warning")}
                  style={{ width: `${m.confidence}%` }}
                />
              </div>
              <span className="w-14 text-right font-mono text-[10px] text-nq-text-secondary">
                {formatPrice(m.prediction)}
              </span>
              <span className="w-8 text-right font-mono text-[10px] text-nq-text-tertiary">
                {(m.weight * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* SHAP Feature Importances */}
      <div>
        <h4 className="mb-2 text-[10px] font-medium text-nq-text-tertiary uppercase tracking-wider">Top Prediction Drivers (SHAP)</h4>
        <div className="space-y-1">
          {FEATURE_IMPORTANCES.map((f) => (
            <div key={f.feature} className="flex items-center gap-2">
              <span className="w-24 text-[10px] text-nq-text-secondary truncate">{f.feature}</span>
              <div className="flex-1 h-1 rounded-full bg-nq-bg-elevated overflow-hidden">
                <div
                  className={cn(
                    "h-full rounded-full",
                    f.direction === "bullish" ? "bg-nq-bull" : f.direction === "bearish" ? "bg-nq-bear" : "bg-nq-text-tertiary"
                  )}
                  style={{ width: `${f.importance * 700}%` }}
                />
              </div>
              <Badge variant={f.direction === "bullish" ? "bull" : f.direction === "bearish" ? "bear" : "default"} className="text-[8px] px-1.5 py-0">
                {f.direction}
              </Badge>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
