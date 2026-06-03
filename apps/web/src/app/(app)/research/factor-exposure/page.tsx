"use client";

import { useEffect, useMemo, useState } from "react";
import { contractsApi, type FactorExposureResponse } from "@/lib/contracts-api";

const DEFAULT_SYMBOLS = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"];

function pct(value: number | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;
}

export default function FactorExposurePage(): JSX.Element {
  const [symbol, setSymbol] = useState<string>(DEFAULT_SYMBOLS[0] ?? "RELIANCE.NS");
  const [windowDays, setWindowDays] = useState<number>(126);
  const [data, setData] = useState<FactorExposureResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);
      try {
        const response = await contractsApi.getFactorExposure(symbol, windowDays);
        if (!mounted) {
          return;
        }
        setData(response);
      } catch (requestError) {
        if (!mounted) {
          return;
        }
        const message = requestError instanceof Error ? requestError.message : "Unable to load factor exposure contract.";
        setError(message);
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    void load();

    return () => {
      mounted = false;
    };
  }, [symbol, windowDays]);

  const exposureRows = useMemo(() => data?.exposures ?? [], [data?.exposures]);
  const metrics = useMemo(() => data?.metrics ?? {}, [data?.metrics]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-semibold">Factor Exposure</h2>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={symbol}
            onChange={(event) => setSymbol(event.target.value)}
            className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1 text-xs"
          >
            {DEFAULT_SYMBOLS.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
          <select
            value={windowDays}
            onChange={(event) => setWindowDays(Number(event.target.value) || 126)}
            className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1 text-xs"
          >
            <option value={126}>126d</option>
            <option value={252}>252d</option>
            <option value={504}>504d</option>
          </select>
        </div>
      </div>

      <p className="text-sm text-[var(--nq-text-secondary)]">Rolling factor decomposition and attribution diagnostics using live research contracts.</p>
      {error ? <p className="text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      <div className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
        <h3 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Current Exposures ({data?.window_days ?? windowDays}d)</h3>
        <div className="space-y-2 text-xs">
          {(loading ? [] : exposureRows).map((row) => {
            const width = Math.min(100, Math.round(Math.abs(row.beta) * 100));
            return (
              <div key={row.factor} className="grid grid-cols-[120px_1fr_56px] items-center gap-3">
                <span className="text-[var(--nq-text-secondary)]">{row.factor}</span>
                <div className="h-3 rounded bg-[rgba(255,255,255,0.05)]">
                  <div
                    className="h-full rounded"
                    style={{
                      width: `${width}%`,
                      background: row.beta >= 0 ? "rgba(0,230,118,0.58)" : "rgba(255,59,92,0.58)",
                    }}
                  />
                </div>
                <span className="text-right">{row.beta.toFixed(2)}</span>
              </div>
            );
          })}
          {!loading && exposureRows.length === 0 ? <p className="text-[var(--nq-text-secondary)]">No exposure rows returned.</p> : null}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {[
          ["Alpha (annualized)", pct(metrics.alpha_annualized)],
          ["Tracking Error", pct(metrics.tracking_error)],
          ["Information Ratio", typeof metrics.information_ratio === "number" ? metrics.information_ratio.toFixed(2) : "--"],
          ["Factor Concentration", typeof metrics.factor_concentration === "number" ? metrics.factor_concentration.toFixed(2) : "--"],
          ["Residual Volatility", pct(metrics.residual_volatility)],
          ["Active Share", pct(metrics.active_share)],
        ].map(([label, value]) => (
          <div key={label} className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3 text-sm">
            <div className="text-xs text-[var(--nq-text-secondary)]">{label}</div>
            <div className="mt-1 font-semibold">{loading ? "..." : value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
