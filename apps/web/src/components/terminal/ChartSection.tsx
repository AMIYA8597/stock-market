"use client";

import { useEffect, useMemo, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { marketApi } from "@/lib/api-client";
import type { OHLCVBar } from "@neuroquant/types";
import type { SignalResponse } from "@/types/intelligence";

interface ChartSectionProps {
  signal: SignalResponse | null;
}

interface WeightPoint {
  model: string;
  weight: number;
}

export default function ChartSection({ signal }: ChartSectionProps): JSX.Element {
  const [bars, setBars] = useState<OHLCVBar[]>([]);

  const weightData: WeightPoint[] = signal
    ? Object.entries(signal.model_weights).map(([model, weight]) => ({ model, weight }))
    : [];
  const confidence = signal ? (signal.ensemble.confidence * 100).toFixed(1) : "--";

  useEffect(() => {
    let mounted = true;

    async function loadHistory(): Promise<void> {
      if (!signal?.symbol) {
        setBars([]);
        return;
      }

      try {
        const history = await marketApi.getHistory(signal.symbol, "1D");
        if (mounted) {
          setBars(history.bars.slice(-30));
        }
      } catch {
        if (mounted) {
          setBars([]);
        }
      }
    }

    void loadHistory();
    return () => {
      mounted = false;
    };
  }, [signal?.symbol]);

  const chartShape = useMemo(() => {
    if (bars.length < 2) {
      return [] as number[];
    }

    const closes = bars.map((bar) => bar.close);
    const min = Math.min(...closes);
    const max = Math.max(...closes);
    const range = max - min || 1;
    return closes.map((value) => 20 + ((value - min) / range) * 75);
  }, [bars]);

  return (
    <section className="flex min-h-[44vh] flex-col bg-[var(--nq-bg-primary)] p-3 lg:min-h-0">
      <div className="mb-3 flex items-center justify-between rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-2">
        <div>
          <h2 className="font-mono text-sm text-[var(--nq-text-primary)]">{signal?.symbol ?? "Select symbol"}</h2>
          <p className="text-xs text-[var(--nq-text-secondary)]">Regime {signal?.regime.state ?? "-"} | Confidence {confidence}%</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-[var(--nq-text-secondary)]">Ensemble</p>
          <p className="text-sm text-[var(--nq-text-primary)]">{signal?.ensemble.direction ?? "-"}</p>
        </div>
      </div>

      <div className="grid h-full grid-rows-[1.4fr_1fr] gap-3 lg:grid-rows-[2fr_1fr]">
        <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Price and signal canvas</p>
          <div className="relative aspect-video overflow-hidden rounded border border-[var(--nq-border-hover)] bg-[linear-gradient(180deg,rgba(0,212,255,0.08),rgba(0,0,0,0))] p-3 lg:aspect-auto lg:h-[85%]">
            <svg viewBox="0 0 240 100" className="h-full w-full" preserveAspectRatio="none" aria-label="Price sparkline">
              <defs>
                <linearGradient id="priceFill" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="rgba(0,212,255,0.35)" />
                  <stop offset="100%" stopColor="rgba(0,212,255,0.02)" />
                </linearGradient>
              </defs>
              <polyline
                fill="none"
                stroke="rgba(0,212,255,0.95)"
                strokeWidth="2"
                points={
                  chartShape.length > 0
                    ? chartShape.map((value, index) => `${(index / (chartShape.length - 1)) * 240},${100 - value}`).join(" ")
                    : ""
                }
              />
              <polygon
                fill="url(#priceFill)"
                points={
                  chartShape.length > 0
                    ? `0,100 ${chartShape.map((value, index) => `${(index / (chartShape.length - 1)) * 240},${100 - value}`).join(" ")} 240,100`
                    : ""
                }
              />
            </svg>
            {chartShape.length === 0 ? (
              <div className="absolute inset-0 flex items-center justify-center bg-[rgba(7,9,15,0.48)]">
                <span className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1 text-xs text-[var(--nq-text-secondary)]">
                  No market history returned for {signal?.symbol ?? "selected symbol"}
                </span>
              </div>
            ) : null}
            <div className="absolute left-3 top-3 rounded border border-[var(--nq-border)] bg-[rgba(5,12,22,0.9)] px-2 py-1 text-[10px] text-[var(--nq-text-secondary)] sm:text-xs">
              Live overlay active: price, signal, regime bands
            </div>
          </div>
        </div>
        <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Dynamic model weights</p>
          <div className="h-[140px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={weightData} margin={{ top: 8, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />
                <XAxis dataKey="model" tick={{ fill: "#8B9BB4", fontSize: 11 }} />
                <YAxis tick={{ fill: "#8B9BB4", fontSize: 11 }} domain={[0, 0.5]} />
                <Tooltip
                  contentStyle={{
                    background: "#121826",
                    border: "1px solid #263349",
                    borderRadius: 8,
                    color: "#E8EAED",
                  }}
                />
                <Line type="monotone" dataKey="weight" stroke="#00D4FF" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </section>
  );
}
