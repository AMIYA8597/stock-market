"use client";

import { useEffect, useMemo, useState } from "react";
import { Search, Download, Star, BookmarkPlus } from "lucide-react";
import Link from "next/link";
import {
  Card, CardHeader, CardTitle, Button, Badge, Input, Sparkline,
  cn, formatPrice, formatPercent, formatCompact, getPriceColor, getDirectionArrow,
} from "@neuroquant/ui";
import { screenerApi } from "@/lib/api-client";
import type { ScreenerFilter, ScreenerResponse } from "@neuroquant/types";

interface ScreenerPreset {
  name: string;
  description: string;
  filters_json: Record<string, unknown>;
}

function sparkDataFromPrice(price: number, drift: number): number[] {
  const base = Number.isFinite(price) ? price : 0;
  const delta = (Number.isFinite(drift) ? drift : 0) / 100;
  return [
    base * (1 - delta * 0.7),
    base * (1 - delta * 0.45),
    base * (1 - delta * 0.2),
    base * (1 + delta * 0.05),
    base * (1 + delta * 0.2),
    base * (1 + delta * 0.35),
    base,
  ];
}

export function ScreenerContent() {
  const [presets, setPresets] = useState<ScreenerPreset[]>([]);
  const [activePreset, setActivePreset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<ScreenerResponse["results"]>([]);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState<Partial<ScreenerFilter>>({
    exchange: "NSE",
    rsi_min: 0,
    rsi_max: 100,
    min_market_cap: 1000,
    above_sma_200: true,
    volume_surge: false,
    ml_confidence_min: 70,
    sort_by: "market_cap",
    sort_order: "desc",
    limit: 50,
    offset: 0,
  });

  const runScreener = async (nextFilters: Partial<ScreenerFilter>): Promise<void> => {
    try {
      setLoading(true);
      setError(null);
      const response = await screenerApi.search(nextFilters);
      setResults(response.results);
      setTotal(response.total);
    } catch (fetchError) {
      const message =
        fetchError instanceof Error ? fetchError.message : "Failed to run screener.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;

    const bootstrap = async () => {
      try {
        const presetData = await screenerApi.getPresets();
        if (isMounted) {
          setPresets(presetData);
        }
      } catch {
        if (isMounted) {
          setPresets([]);
        }
      }

      if (isMounted) {
        void runScreener(filters);
      }
    };

    void bootstrap();
    return () => {
      isMounted = false;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const visiblePresets = useMemo(() => {
    if (presets.length > 0) {
      return presets.map((preset) => ({
        label: preset.name.replaceAll("_", " "),
        desc: preset.description,
      }));
    }
    return [
      { label: "Value Stocks", desc: "Low valuation high-quality basket" },
      { label: "Momentum", desc: "High momentum and trend strength" },
      { label: "Oversold RSI", desc: "Oversold rebounds" },
    ];
  }, [presets]);

  const updateFilter = (key: keyof ScreenerFilter, value: number | boolean | string | undefined): void => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl font-bold text-nq-text-primary">AI Stock Screener</h1>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm"><BookmarkPlus className="h-3.5 w-3.5" /> Save Screen</Button>
          <Button variant="secondary" size="sm"><Download className="h-3.5 w-3.5" /> Export CSV</Button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4">
        {/* Filter panel */}
        <div className="col-span-12 lg:col-span-3 space-y-4">
          <Card>
            <CardHeader><CardTitle>Presets</CardTitle></CardHeader>
            <div className="space-y-1.5">
              {visiblePresets.map((preset, i) => (
                <button
                  key={preset.label}
                  onClick={() => setActivePreset(i)}
                  className={cn(
                    "w-full rounded-nq px-3 py-2 text-left transition-colors",
                    activePreset === i ? "bg-nq-accent/10 border border-nq-accent/20" : "hover:bg-nq-bg-elevated border border-transparent"
                  )}
                >
                  <div className="text-xs font-medium capitalize text-nq-text-primary">{preset.label}</div>
                  <div className="text-[10px] text-nq-text-tertiary mt-0.5">{preset.desc}</div>
                </button>
              ))}
            </div>
          </Card>

          <Card>
            <CardHeader><CardTitle>Filters</CardTitle></CardHeader>
            <div className="space-y-3">
              {[
                { label: "RSI Range", min: "0", max: "100" },
                { label: "Market Cap (Cr)", min: "1000", max: "" },
              ].map((f) => (
                <div key={f.label}>
                  <label className="text-[10px] text-nq-text-tertiary mb-1 block">{f.label}</label>
                  <div className="flex gap-2">
                    <Input
                      placeholder="Min"
                      defaultValue={f.min}
                      className="h-7 text-[11px]"
                      onChange={(event) => {
                        const value = event.target.value;
                        if (f.label === "RSI Range") {
                          updateFilter("rsi_min", value ? Number(value) : undefined);
                        }
                        if (f.label === "Market Cap (Cr)") {
                          updateFilter("min_market_cap", value ? Number(value) : undefined);
                        }
                      }}
                    />
                    <Input
                      placeholder="Max"
                      defaultValue={f.max}
                      className="h-7 text-[11px]"
                      onChange={(event) => {
                        const value = event.target.value;
                        if (f.label === "RSI Range") {
                          updateFilter("rsi_max", value ? Number(value) : undefined);
                        }
                        if (f.label === "Market Cap (Cr)") {
                          updateFilter("max_market_cap", value ? Number(value) : undefined);
                        }
                      }}
                    />
                  </div>
                </div>
              ))}
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={Boolean(filters.above_sma_200)}
                  onChange={(event) => updateFilter("above_sma_200", event.target.checked)}
                  className="rounded border-nq-border bg-nq-bg-secondary"
                />
                <span className="text-xs text-nq-text-secondary">Above SMA 200</span>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={Boolean(filters.volume_surge)}
                  onChange={(event) => updateFilter("volume_surge", event.target.checked)}
                  className="rounded border-nq-border bg-nq-bg-secondary"
                />
                <span className="text-xs text-nq-text-secondary">Volume Surge (&gt;2x avg)</span>
              </div>
              <div>
                <label className="text-[10px] text-nq-text-tertiary mb-1 block">AI Confidence Min</label>
                <Input
                  type="number"
                  placeholder="70"
                  defaultValue="70"
                  className="h-7 text-[11px]"
                  onChange={(event) => updateFilter("ml_confidence_min", Number(event.target.value))}
                />
              </div>
              <Button className="w-full" size="sm" onClick={() => void runScreener(filters)} disabled={loading}>
                <Search className="h-3.5 w-3.5" />
                {loading ? "Running..." : "Run Screener"}
              </Button>
            </div>
          </Card>
        </div>

        {/* Results table */}
        <div className="col-span-12 lg:col-span-9">
          <Card noPadding>
            <CardHeader className="px-4 pt-3">
              <CardTitle>{loading ? "Loading..." : `${total} stocks found`}</CardTitle>
              <Badge variant="accent">Live</Badge>
            </CardHeader>
            {error ? (
              <div className="px-4 pb-4 text-xs text-nq-bear">{error}</div>
            ) : null}
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-nq-border bg-nq-bg-elevated/50">
                    {["Symbol", "Price", "Chg%", "Volume", "Mkt Cap", "RSI", "AI Signal", "Conf", ""].map((h) => (
                      <th key={h} className="px-3 py-2 text-left text-[10px] font-medium text-nq-text-tertiary uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-nq-border">
                  {results.map((r) => {
                    const spark = sparkDataFromPrice(r.price, r.change_percent);
                    return (
                    <tr key={r.symbol} className="hover:bg-nq-bg-card/50 transition-colors cursor-pointer">
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <div>
                            <Link href={`/markets/stocks/${encodeURIComponent(r.symbol)}`} className="font-mono font-semibold text-nq-text-primary hover:text-nq-accent">
                              {r.symbol}
                            </Link>
                            <div className="text-[10px] text-nq-text-tertiary">{r.sector ?? "-"}</div>
                          </div>
                          <Sparkline data={spark} width={40} height={14} />
                        </div>
                      </td>
                      <td className="px-3 py-2.5 font-mono font-semibold text-nq-text-primary">{formatPrice(r.price)}</td>
                      <td className={cn("px-3 py-2.5 font-mono font-medium", getPriceColor(r.change_percent))}>
                        {getDirectionArrow(r.change_percent)} {formatPercent(r.change_percent)}
                      </td>
                      <td className="px-3 py-2.5 font-mono text-nq-text-secondary">{r.volume > 0 ? formatCompact(r.volume) : "-"}</td>
                      <td className="px-3 py-2.5 font-mono text-nq-text-secondary">{r.market_cap ? formatCompact(r.market_cap) : "-"}</td>
                      <td className="px-3 py-2.5 font-mono text-nq-text-secondary">{r.rsi ?? "-"}</td>
                      <td className="px-3 py-2.5">
                        <Badge variant={r.ml_signal === "BUY" ? "bull" : r.ml_signal === "SELL" ? "bear" : "default"}>{r.ml_signal ?? "HOLD"}</Badge>
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-1">
                          <div className="w-12 h-1.5 rounded-full bg-nq-bg-elevated overflow-hidden">
                            <div className="h-full rounded-full bg-nq-accent" style={{ width: `${r.ml_confidence ?? 0}%` }} />
                          </div>
                          <span className="font-mono text-[10px] text-nq-text-tertiary">{r.ml_confidence ?? 0}%</span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5">
                        <Button variant="ghost" size="sm" className="h-6 text-[10px]"><Star className="h-3 w-3" /></Button>
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
