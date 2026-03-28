"use client";

import { useEffect, useMemo, useState } from "react";

import { marketApi } from "@/lib/api-client";
import type { OHLCVBar } from "@neuroquant/types";
import type { SignalResponse } from "@/types/intelligence";
import { LightweightCandlestickChart, SimpleLineAreaChart, type LineAreaPoint, SimpleBarChart, type SimpleBarPoint } from "@/components/charts";

interface ChartSectionProps {
  signal: SignalResponse | null;
}

export default function ChartSection({ signal }: ChartSectionProps): JSX.Element {
  const [bars, setBars] = useState<OHLCVBar[]>([]);
  const [timeframe, setTimeframe] = useState<"1D" | "1H" | "15M" | "5M" | "1M">("1D");
  const [subTab, setSubTab] = useState<"indicators" | "signals" | "orderflow">("signals");

  const weightData: SimpleBarPoint[] = signal
    ? Object.entries(signal.model_weights).map(([model, weight]) => ({
        label: model,
        value: weight,
        color: "rgba(0,212,245,0.6)",
      }))
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
        const history = await marketApi.getHistory(signal.symbol, timeframe);
        if (mounted) {
          setBars(history.bars.slice(-180));
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
  }, [signal?.symbol, timeframe]);

  const indicatorSeries = useMemo<LineAreaPoint[]>(() => {
    if (bars.length === 0) {
      return [];
    }
    const closes = bars.slice(-60).map((bar) => bar.close);
    const first = closes[0] ?? 1;
    return closes.map((close, index) => ({ label: String(index + 1), value: ((close / first) - 1) * 100 }));
  }, [bars]);

  const orderFlowBars = useMemo<SimpleBarPoint[]>(() => {
    if (bars.length === 0) {
      return [];
    }
    return bars.slice(-40).map((bar, index) => {
      const imbalance = bar.close - bar.open;
      return {
        label: String(index + 1),
        value: Math.abs(imbalance),
        color: imbalance >= 0 ? "rgba(0,230,118,0.6)" : "rgba(255,59,92,0.6)",
      };
    });
  }, [bars]);

  return (
    <section className="flex min-h-[44vh] flex-col bg-[var(--nq-bg-primary)] p-3 lg:min-h-0">
      <div className="mb-3 flex items-center justify-between rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-2">
        <div>
          <h2 className="font-mono text-sm text-[var(--nq-text-primary)]">{signal?.symbol ?? "Select symbol"}</h2>
          <p className="text-xs text-[var(--nq-text-secondary)]">Regime {signal?.regime.state ?? "-"} | Confidence {confidence}%</p>
        </div>
        <div className="flex items-center gap-1">
          {(["1M", "5M", "15M", "1H", "1D"] as const).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setTimeframe(value)}
              className={`rounded border px-2 py-1 text-[10px] ${timeframe === value ? "border-[var(--nq-accent-cyan)] bg-[rgba(0,212,245,0.12)] text-[var(--nq-text-primary)]" : "border-[var(--nq-border)] text-[var(--nq-text-secondary)]"}`}
            >
              {value}
            </button>
          ))}
        </div>
      </div>

      <div className="grid h-full grid-rows-[1.4fr_1fr] gap-3 lg:grid-rows-[2fr_1fr]">
        <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Price and signal canvas</p>
          <div className="relative aspect-video overflow-hidden rounded border border-[var(--nq-border-hover)] bg-[linear-gradient(180deg,rgba(0,212,255,0.08),rgba(0,0,0,0))] p-3 lg:aspect-auto lg:h-[85%]">
            {bars.length > 0 ? <LightweightCandlestickChart bars={bars} /> : null}
            {bars.length === 0 ? (
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
          <div className="mb-2 flex items-center gap-1">
            {([
              ["indicators", "Indicators"],
              ["signals", "Signals"],
              ["orderflow", "Order Flow"],
            ] as const).map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setSubTab(key)}
                className={`rounded border px-2 py-1 text-[10px] ${subTab === key ? "border-[var(--nq-accent-cyan)] bg-[rgba(0,212,245,0.12)] text-[var(--nq-text-primary)]" : "border-[var(--nq-border)] text-[var(--nq-text-secondary)]"}`}
              >
                {label}
              </button>
            ))}
          </div>
          <div className="h-[140px] rounded bg-[rgba(255,255,255,0.02)] p-2">
            {subTab === "signals" ? <SimpleBarChart data={weightData.map((item) => ({ ...item, label: item.label.slice(0, 8) }))} yTickFormatter={(value) => `${(value * 100).toFixed(0)}%`} /> : null}
            {subTab === "indicators" ? <SimpleLineAreaChart data={indicatorSeries.length > 0 ? indicatorSeries : [{ label: "1", value: 0 }]} mode="line" stroke="var(--nq-accent-purple)" yTickFormatter={(value) => `${value.toFixed(2)}%`} /> : null}
            {subTab === "orderflow" ? <SimpleBarChart data={orderFlowBars.length > 0 ? orderFlowBars : [{ label: "1", value: 0, color: "rgba(255,255,255,0.2)" }]} /> : null}
          </div>
        </div>
      </div>
    </section>
  );
}
