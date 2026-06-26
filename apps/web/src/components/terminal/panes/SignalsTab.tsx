"use client";

import type { SignalResponse, ForecastPoint } from "@/types/intelligence";
import { safeFormat } from "@/lib/formatters";

interface SignalsTabProps {
  signal: SignalResponse | null;
  forecast?: ForecastPoint[] | null;
}

const BidirectionalBar = ({ score, min = -1.0, max = 1.0 }: { score: number; min?: number; max?: number }) => {
  const percentage = Math.abs(score / (max - min)) * 100; // percentage of half
  const isPositive = score >= 0;
  
  return (
    <div className="relative h-2 w-full bg-[rgba(255,255,255,0.03)] rounded-full overflow-hidden border border-[var(--nq-border)]">
      {/* Zero line in center */}
      <div className="absolute top-0 bottom-0 left-1/2 w-px bg-[rgba(255,255,255,0.15)] z-10" />
      {/* Bidirectional filled bar */}
      <div
        className={`absolute top-0 bottom-0 transition-all duration-500 ${isPositive ? "bg-[var(--nq-accent-green)]" : "bg-[var(--nq-accent-red)]"}`}
        style={{
          width: `${Math.min(50, percentage * 0.5)}%`,
          left: isPositive ? "50%" : "auto",
          right: !isPositive ? "50%" : "auto"
        }}
      />
    </div>
  );
};

export default function SignalsTab({ signal, forecast }: SignalsTabProps): JSX.Element {
  if (!signal) {
    return (
      <div className="flex h-full items-center justify-center p-4 text-[10px] font-mono text-[var(--nq-text-muted)]">
        Waiting for active signal feed...
      </div>
    );
  }

  // 1. Confidence Gauge Math
  const confidenceVal = Number(signal.ensemble.confidence ?? 0.50);
  const direction = signal.ensemble.direction ?? "NEUTRAL";
  const radius = 34;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (confidenceVal * circumference);
  
  let strokeColor = "var(--nq-accent-amber)";
  if (direction.includes("BUY")) strokeColor = "var(--nq-accent-green)";
  if (direction.includes("SELL")) strokeColor = "var(--nq-accent-red)";

  // 2. Safe helper to extract model properties
  const technical = signal.models.technical || {};
  const pattern = signal.models.pattern || {};
  const momentum = signal.models.momentum || {};
  const regime = signal.models.regime || {};
  const xgboost = signal.models.xgboost || {};

  const technicalScore = Number(technical.score ?? 0);
  const patternScore = Number(pattern.pattern_score ?? 0);
  const momentumScore = Number(momentum.momentum_score ?? 0);
  const xgbScore = Number(xgboost.raw_signal ?? 0);
  const trainSamples = xgboost.train_samples ?? 0;
  const detectedPatterns = Array.isArray(pattern.patterns_detected) ? pattern.patterns_detected : [];

  return (
    <div className="grid h-full grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 p-1 font-sans">
      {/* Section 1: Confidence Gauge */}
      <div className="flex flex-col items-center justify-center rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3 min-h-[160px]">
        <p className="text-[9px] uppercase tracking-wider text-[var(--nq-text-secondary)] font-semibold mb-2">
          Ensemble Confidence
        </p>
        <div className="relative h-24 w-24">
          <svg className="h-full w-full -rotate-90">
            <circle
              cx="48"
              cy="48"
              r={radius}
              stroke="rgba(255,255,255,0.03)"
              strokeWidth="6"
              fill="transparent"
            />
            <circle
              cx="48"
              cy="48"
              r={radius}
              stroke={strokeColor}
              strokeWidth="6"
              fill="transparent"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              className="transition-all duration-500 ease-out"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center font-mono">
            <span className="text-sm font-bold text-[var(--nq-text-primary)]">
              {safeFormat(confidenceVal * 100, 1)}%
            </span>
            <span className={`text-[7px] font-semibold tracking-wider ${direction.includes("BUY") ? "text-[var(--nq-accent-green)]" : direction.includes("SELL") ? "text-[var(--nq-accent-red)]" : "text-[var(--nq-accent-amber)]"}`}>
              {direction.replace("_", " ")}
            </span>
          </div>
        </div>
      </div>

      {/* Section 2: Five-Model Score Bars */}
      <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3 font-mono text-[9px] flex flex-col justify-between">
        <div>
          <p className="text-[9px] uppercase tracking-wider text-[var(--nq-text-secondary)] font-sans font-semibold mb-2">
            Model Layer Consensus
          </p>
          <div className="space-y-2.5">
            {/* Technical */}
            <div>
              <div className="flex justify-between mb-0.5">
                <span>Technical indicators</span>
                <span className="font-bold text-[var(--nq-text-primary)]">{safeFormat(technicalScore, 2)}</span>
              </div>
              <BidirectionalBar score={technicalScore} />
            </div>

            {/* Patterns */}
            <div>
              <div className="flex justify-between mb-0.5">
                <span>Candlestick Patterns</span>
                <span className="font-bold text-[var(--nq-text-primary)]">{safeFormat(patternScore, 2)}</span>
              </div>
              <BidirectionalBar score={patternScore} />
            </div>

            {/* Momentum */}
            <div>
              <div className="flex justify-between mb-0.5">
                <span>Momentum factor</span>
                <span className="font-bold text-[var(--nq-text-primary)]">{safeFormat(momentumScore, 2)}</span>
              </div>
              <BidirectionalBar score={momentumScore} />
            </div>

            {/* Regime */}
            <div>
              <div className="flex justify-between mb-0.5 items-center">
                <span>Regime (Bull prob)</span>
                <span className="rounded bg-[rgba(255,255,255,0.05)] border border-[var(--nq-border)] px-1 py-0.2 text-[7px] text-[var(--nq-text-primary)] uppercase font-semibold">
                  {regime.regime ?? "SIDEWAYS"}
                </span>
              </div>
              <div className="relative h-2 w-full bg-[rgba(255,255,255,0.03)] rounded-full overflow-hidden border border-[var(--nq-border)]">
                <div
                  className="h-full bg-[var(--nq-accent-green)] transition-all duration-500"
                  style={{ width: `${(regime.bull_prob ?? 0.5) * 100}%` }}
                />
              </div>
            </div>

            {/* XGBoost */}
            <div>
              <div className="flex justify-between mb-0.5">
                <span>XGBoost Classifier</span>
                <span className="font-bold text-[var(--nq-text-primary)]">{safeFormat(xgbScore, 2)}</span>
              </div>
              <BidirectionalBar score={xgbScore} />
              <div className="text-[7px] text-[var(--nq-text-muted)] mt-0.5">
                Train samples: {trainSamples} observations
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Section 3: Indicator Pills */}
      <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3 flex flex-col justify-between font-mono text-[9px]">
        <div>
          <p className="text-[9px] uppercase tracking-wider text-[var(--nq-text-secondary)] font-sans font-semibold mb-2">
            Technical Oscillators
          </p>
          <div className="grid grid-cols-2 gap-1.5">
            {/* RSI */}
            <div className="rounded bg-[rgba(255,255,255,0.02)] border border-[var(--nq-border)] p-1">
              <span className="block text-[7px] text-[var(--nq-text-secondary)]">RSI (14)</span>
              <strong className={`text-xs ${Number(technical.rsi) < 40 ? "text-[var(--nq-accent-green)]" : Number(technical.rsi) > 60 ? "text-[var(--nq-accent-red)]" : "text-[var(--nq-accent-amber)]"}`}>
                {safeFormat(technical.rsi, 1)}
              </strong>
            </div>

            {/* MACD */}
            <div className="rounded bg-[rgba(255,255,255,0.02)] border border-[var(--nq-border)] p-1">
              <span className="block text-[7px] text-[var(--nq-text-secondary)]">MACD Hist</span>
              <strong className={`text-xs ${Number(technical.macd_histogram) >= 0 ? "text-[var(--nq-accent-green)]" : "text-[var(--nq-accent-red)]"}`}>
                {Number(technical.macd_histogram) >= 0 ? "+" : ""}{safeFormat(technical.macd_histogram, 2)}
              </strong>
            </div>

            {/* SuperTrend */}
            <div className="rounded bg-[rgba(255,255,255,0.02)] border border-[var(--nq-border)] p-1">
              <span className="block text-[7px] text-[var(--nq-text-secondary)]">SuperTrend</span>
              <strong className={`text-xs ${Number(technical.supertrend_direction) === 1 ? "text-[var(--nq-accent-green)]" : "text-[var(--nq-accent-red)]"}`}>
                {Number(technical.supertrend_direction) === 1 ? "Bullish" : "Bearish"}
              </strong>
            </div>

            {/* ADX */}
            <div className="rounded bg-[rgba(255,255,255,0.02)] border border-[var(--nq-border)] p-1">
              <span className="block text-[7px] text-[var(--nq-text-secondary)]">ADX Trend</span>
              <strong className="text-xs text-[var(--nq-text-primary)]">
                {safeFormat(technical.adx, 1)}
              </strong>
            </div>

            {/* VWAP */}
            <div className="col-span-2 rounded bg-[rgba(255,255,255,0.02)] border border-[var(--nq-border)] p-1 flex justify-between items-center">
              <div>
                <span className="block text-[7px] text-[var(--nq-text-secondary)]">VWAP Position</span>
                <strong className={`text-xs ${technical.above_vwap ? "text-[var(--nq-accent-green)]" : "text-[var(--nq-accent-red)]"}`}>
                  {technical.above_vwap ? "Above" : "Below"}
                </strong>
              </div>
              <span className="text-[7px] text-[var(--nq-text-muted)]">
                ATR (14): {safeFormat(technical.atr, 2)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Section 4: Pattern Chips */}
      <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3 flex flex-col justify-between min-h-[120px]">
        <div>
          <p className="text-[9px] uppercase tracking-wider text-[var(--nq-text-secondary)] font-semibold mb-2">
            Detected Candlestick Patterns
          </p>
          <div className="flex flex-wrap gap-1 max-h-[70px] overflow-y-auto ds-scrollable mb-2">
            {detectedPatterns.map((pat) => (
              <span
                key={pat}
                className="rounded px-1.5 py-0.5 text-[8px] font-mono uppercase font-bold bg-[rgba(0,212,245,0.08)] text-[var(--nq-accent-cyan)] border border-[rgba(0,212,245,0.15)]"
              >
                {pat.replace("CDL_", "").replace("_", " ")}
              </span>
            ))}
            {detectedPatterns.length === 0 && (
              <span className="text-[9px] font-mono text-[var(--nq-text-muted)] italic">
                No patterns identified on last 10 candles.
              </span>
            )}
          </div>
        </div>
        <div className="border-t border-[var(--nq-border)] pt-1.5 flex justify-between text-[8px] font-mono text-[var(--nq-text-secondary)]">
          <span>Bullish patterns: {pattern.bullish_count ?? 0}</span>
          <span>Bearish patterns: {pattern.bearish_count ?? 0}</span>
        </div>
      </div>

      {/* Section 5: Detailed Layer Outputs Table */}
      <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3 xl:col-span-2 flex flex-col justify-between">
        <div>
          <p className="text-[9px] uppercase tracking-wider text-[var(--nq-text-secondary)] font-semibold mb-2">
            Detailed Layer Outputs
          </p>
          <table className="w-full text-left font-mono text-[9px] border-collapse">
            <thead>
              <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-muted)] font-sans font-bold">
                <th className="pb-1">Model Layer</th>
                <th className="pb-1 text-right">Consensus Score</th>
                <th className="pb-1 text-right">Signal Direction</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(signal.models).map(([model, data]) => {
                const getModelScore = (name: string, d: Record<string, unknown>) => {
                  if (name === "technical") return (d.score as number) ?? 0;
                  if (name === "pattern") return (d.pattern_score as number) ?? 0;
                  if (name === "momentum") return (d.momentum_score as number) ?? 0;
                  if (name === "regime") return (d.bull_prob as number) ?? 0.5;
                  if (name === "xgboost") return (d.xgb_score as number) ?? 0;
                  return 0;
                };

                const getModelDirection = (name: string, d: Record<string, unknown>) => {
                  if (name === "regime") return (d.regime as string) ?? "SIDEWAYS";
                  if (name === "xgboost") return (d.xgb_direction as string) ?? "NEUTRAL";
                  const s = getModelScore(name, d);
                  if (s > 0.15) return "BUY";
                  if (s < -0.15) return "SELL";
                  return "NEUTRAL";
                };

                const score = getModelScore(model, data as Record<string, unknown>);
                const dir = getModelDirection(model, data as Record<string, unknown>);
                let dirColor = "text-[var(--nq-accent-amber)]";
                if (dir.includes("BUY")) dirColor = "text-[var(--nq-accent-green)]";
                if (dir.includes("SELL")) dirColor = "text-[var(--nq-accent-red)]";

                return (
                  <tr key={model} className="border-b border-[rgba(255,255,255,0.02)] hover:bg-[rgba(255,255,255,0.01)] text-[var(--nq-text-secondary)]">
                    <td className="py-1 uppercase font-bold text-[var(--nq-text-primary)]">{model}</td>
                    <td className="py-1 text-right font-mono">{safeFormat(score, 4)}</td>
                    <td className={`py-1 text-right font-bold ${dirColor}`}>{dir.replace("_", " ")}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Section 6: Forecast Table */}
      <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3 sm:col-span-2 xl:col-span-3">
        <p className="text-[9px] uppercase tracking-wider text-[var(--nq-text-secondary)] font-semibold mb-2">
          Multi-Horizon SARIMAX Price Projection
        </p>
        <div className="overflow-x-auto ds-scrollable max-h-[140px]">
          <table className="w-full text-left font-mono text-[9px] border-collapse">
            <thead>
              <tr className="border-b border-[var(--nq-border)] text-[var(--nq-text-muted)] font-sans font-bold">
                <th className="pb-1">Horizon</th>
                <th className="pb-1">Target Date</th>
                <th className="pb-1 text-right">Predicted Price</th>
                <th className="pb-1 text-right">Expected Change</th>
                <th className="pb-1 text-right">80% Conf. Low</th>
                <th className="pb-1 text-right">80% Conf. High</th>
              </tr>
            </thead>
            <tbody>
              {(forecast || []).map((pt) => {
                const changePct = pt.change_pct ?? 0;
                const isPositive = changePct >= 0;
                return (
                  <tr key={pt.horizon_days} className="border-b border-[rgba(255,255,255,0.02)] text-[var(--nq-text-secondary)] hover:bg-[rgba(255,255,255,0.01)]">
                    <td className="py-1">{pt.horizon_days}d</td>
                    <td className="py-1">{pt.target_date}</td>
                    <td className="py-1 text-right text-[var(--nq-text-primary)] font-semibold">
                      ₹{pt.predicted_price.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className={`py-1 text-right font-semibold ${isPositive ? "text-[var(--nq-accent-green)]" : "text-[var(--nq-accent-red)]"}`}>
                      {isPositive ? "+" : ""}{safeFormat(changePct * 100, 2)}%
                    </td>
                    <td className="py-1 text-right opacity-75">
                      ₹{pt.prediction_low.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="py-1 text-right opacity-75">
                      ₹{pt.prediction_high.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                  </tr>
                );
              })}
              {(!forecast || forecast.length === 0) && (
                <tr>
                  <td colSpan={6} className="py-4 text-center text-[var(--nq-text-muted)] italic">
                    No forecast projections available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
