"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { contractsApi, type PortfolioTransactionRequest } from "@/lib/contracts-api";
import { useOrderHistory } from "@/hooks/use-order-history";
import { SimpleDonutChart, type DonutSlice } from "@/components/charts";
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
  const [expandedModel, setExpandedModel] = useState<"tft" | "hmm_garch" | "gnn" | "lstm_attn" | "xgboost">("tft");
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [quantity, setQuantity] = useState<string>("10");
  const [price, setPrice] = useState<string>("0");
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [tradeError, setTradeError] = useState<string | null>(null);
  const [tradeSuccess, setTradeSuccess] = useState<string | null>(null);
  const { orders, addOrder, clearOrders } = useOrderHistory();

  const direction = signal?.ensemble.direction ?? "NEUTRAL";
  const confidence = signal ? (signal.ensemble.confidence * 100).toFixed(1) : "0.0";
  const featureRows = (signal?.models.xgboost.top_features ?? []).slice(0, 5);
  const latestPrice = useMemo(() => {
    const median = signal?.models?.tft?.p50;
    if (typeof median === "number" && Number.isFinite(median) && median > 0) {
      return median;
    }
    return 0;
  }, [signal?.models?.tft?.p50]);

  const confidencePct = Number(confidence);
  const confidenceStroke = Math.max(0, Math.min(100, confidencePct));
  const gaugeCircumference = 2 * Math.PI * 34;
  const gaugeOffset = gaugeCircumference * (1 - confidenceStroke / 100);

  const weightSlices = useMemo<DonutSlice[]>(() => {
    if (!signal?.model_weights) {
      return [];
    }

    const palette = [
      "var(--nq-accent-cyan)",
      "var(--nq-accent-green)",
      "var(--nq-accent-amber)",
      "var(--nq-accent-purple)",
      "var(--nq-accent-red)",
    ];

    return Object.entries(signal.model_weights).map(([name, value], index) => ({
      name,
      value,
      color: palette[index % palette.length] ?? "var(--nq-accent-cyan)",
    }));
  }, [signal?.model_weights]);

  const newsFeed = useMemo(() => {
    const currentSymbol = signal?.symbol ?? "MARKET";
    const directionBias = signal?.ensemble.direction ?? "NEUTRAL";
    const now = new Date();
    return [
      { headline: `${currentSymbol} guidance updates market expectations`, sentiment: "POSITIVE", time: now.toLocaleTimeString() },
      { headline: `Regime shift monitor flags ${currentSymbol} as ${directionBias}`, sentiment: directionBias.includes("SELL") ? "NEGATIVE" : "NEUTRAL", time: new Date(now.getTime() - 12 * 60_000).toLocaleTimeString() },
      { headline: `Cross-asset flow indicates volatility clustering in ${currentSymbol}`, sentiment: "NEUTRAL", time: new Date(now.getTime() - 28 * 60_000).toLocaleTimeString() },
    ];
  }, [signal?.ensemble.direction, signal?.symbol]);

  useEffect(() => {
    if (latestPrice > 0) {
      setPrice(latestPrice.toFixed(4));
    }
  }, [latestPrice]);

  const submitOrder = async (event: FormEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setTradeError(null);
    setTradeSuccess(null);

    if (!signal?.symbol) {
      setTradeError("Select a symbol before placing an order.");
      return;
    }

    const parsedQty = Number(quantity);
    const parsedPrice = Number(price);
    if (!Number.isFinite(parsedQty) || parsedQty <= 0) {
      setTradeError("Quantity must be greater than zero.");
      return;
    }
    if (!Number.isFinite(parsedPrice) || parsedPrice <= 0) {
      setTradeError("Price must be greater than zero.");
      return;
    }

    const payload: PortfolioTransactionRequest = {
      symbol: signal.symbol,
      type: side,
      quantity: parsedQty,
      price: parsedPrice,
    };

    setSubmitting(true);
    try {
      const response = await contractsApi.postPortfolioTransaction(payload);
      addOrder(response, "api");
      setTradeSuccess(`${response.type} ${response.symbol} confirmed.`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Failed to place order.";
      setTradeError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const notional = (() => {
    const parsedQty = Number(quantity);
    const parsedPrice = Number(price);
    if (!Number.isFinite(parsedQty) || !Number.isFinite(parsedPrice)) {
      return 0;
    }
    return parsedQty * parsedPrice;
  })();

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
        <div className="mt-2 grid grid-cols-[88px_1fr] items-center gap-2">
          <svg viewBox="0 0 80 80" className="h-20 w-20" aria-label="Confidence gauge">
            <circle cx="40" cy="40" r="34" fill="none" stroke="rgba(255,255,255,0.10)" strokeWidth="8" />
            <circle
              cx="40"
              cy="40"
              r="34"
              fill="none"
              stroke="var(--nq-accent-cyan)"
              strokeWidth="8"
              strokeLinecap="round"
              strokeDasharray={gaugeCircumference}
              strokeDashoffset={gaugeOffset}
              transform="rotate(-90 40 40)"
            />
            <text x="40" y="44" textAnchor="middle" fontSize="12" fill="var(--nq-text-primary)">{confidenceStroke.toFixed(0)}%</text>
          </svg>
          <div className="text-xs text-[var(--nq-text-secondary)]">
            <p>Kelly {(signal?.ensemble.kelly_fraction ?? 0).toFixed(3)}</p>
            <p className="mt-1">Model spread {signal ? Object.keys(signal.model_weights).length : 0} active engines</p>
          </div>
        </div>
      </div>

      <div className="mb-3 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">EnsembleWeightPie</p>
        <div className="h-[150px]">
          <SimpleDonutChart data={weightSlices.length > 0 ? weightSlices : [{ name: "No Data", value: 1, color: "var(--nq-border)" }]} centerLabel="weights" />
        </div>
      </div>

      <div className="mb-3 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Model breakdown</p>
        <div className="space-y-2 text-xs text-[var(--nq-text-secondary)]">
          {([
            ["tft", `TFT P10 ${signal?.models.tft.p10.toFixed(4) ?? "--"} | P50 ${signal?.models.tft.p50.toFixed(4) ?? "--"} | P90 ${signal?.models.tft.p90.toFixed(4) ?? "--"}`],
            ["hmm_garch", `HMM ${signal?.models.hmm_garch.regime_signal ?? "-"} | Vol 1d ${(signal?.models.hmm_garch.vol_forecast_1d ?? 0).toFixed(4)}`],
            ["gnn", `GNN spillover ${(signal?.models.gnn.spillover_risk ?? 0).toFixed(3)} | Top ${(signal?.models.gnn.top_correlated_assets ?? []).slice(0, 3).join(", ") || "--"}`],
            ["lstm_attn", `LSTM signal ${(signal?.models.lstm_attn.raw_signal ?? 0).toFixed(3)}`],
            ["xgboost", `XGBoost raw ${(signal?.models.xgboost.raw_signal ?? 0).toFixed(3)} | SHAP ${(signal?.models.xgboost.top_features ?? []).slice(0, 3).map((f) => String(f.name)).join(", ") || "--"}`],
          ] as const).map(([key, summary]) => (
            <div key={key} className="rounded border border-[var(--nq-border)]">
              <button
                type="button"
                onClick={() => setExpandedModel(key)}
                className="flex w-full items-center justify-between px-2 py-1.5 text-left"
              >
                <span className="font-medium uppercase text-[var(--nq-text-primary)]">{key}</span>
                <span>{expandedModel === key ? "-" : "+"}</span>
              </button>
              {expandedModel === key ? <p className="border-t border-[var(--nq-border)] px-2 py-1.5 text-[10px]">{summary}</p> : null}
            </div>
          ))}
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

      <div className="mt-3 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Order ticket</p>
        <form className="space-y-2" onSubmit={submitOrder}>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <button
              type="button"
              onClick={() => setSide("BUY")}
              className={`rounded border px-2 py-1.5 ${
                side === "BUY"
                  ? "border-[#00E676] bg-[rgba(0,230,118,0.15)] text-[#00E676]"
                  : "border-[var(--nq-border)] text-[var(--nq-text-secondary)]"
              }`}
            >
              Buy
            </button>
            <button
              type="button"
              onClick={() => setSide("SELL")}
              className={`rounded border px-2 py-1.5 ${
                side === "SELL"
                  ? "border-[#FF3B5C] bg-[rgba(255,59,92,0.15)] text-[#FF3B5C]"
                  : "border-[var(--nq-border)] text-[var(--nq-text-secondary)]"
              }`}
            >
              Sell
            </button>
          </div>

          <label className="block text-xs text-[var(--nq-text-secondary)]">
            Symbol
            <input
              type="text"
              readOnly
              value={signal?.symbol ?? ""}
              className="mt-1 w-full rounded border border-[var(--nq-border)] bg-[var(--nq-bg-elevated)] px-2 py-1.5 text-[var(--nq-text-primary)]"
            />
          </label>

          <div className="grid grid-cols-2 gap-2">
            <label className="block text-xs text-[var(--nq-text-secondary)]">
              Quantity
              <input
                type="number"
                min="0.0001"
                step="0.0001"
                value={quantity}
                onChange={(event) => setQuantity(event.target.value)}
                className="mt-1 w-full rounded border border-[var(--nq-border)] bg-[var(--nq-bg-elevated)] px-2 py-1.5 text-[var(--nq-text-primary)]"
              />
            </label>
            <label className="block text-xs text-[var(--nq-text-secondary)]">
              Price
              <input
                type="number"
                min="0.0001"
                step="0.0001"
                value={price}
                onChange={(event) => setPrice(event.target.value)}
                className="mt-1 w-full rounded border border-[var(--nq-border)] bg-[var(--nq-bg-elevated)] px-2 py-1.5 text-[var(--nq-text-primary)]"
              />
            </label>
          </div>

          <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-2 py-1.5 text-xs text-[var(--nq-text-secondary)]">
            Estimated notional: {Number.isFinite(notional) ? notional.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : "--"}
          </div>

          {tradeError ? <p className="text-xs text-[#FF3B5C]">{tradeError}</p> : null}
          {tradeSuccess ? <p className="text-xs text-[#00E676]">{tradeSuccess}</p> : null}

          <button
            type="submit"
            disabled={submitting || !signal?.symbol}
            className="w-full rounded border border-[var(--nq-border)] bg-[var(--nq-bg-elevated)] px-3 py-2 text-xs font-semibold text-[var(--nq-text-primary)] transition hover:border-[var(--nq-border-hover)] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? "Placing order..." : `Place ${side} Order`}
          </button>
        </form>
      </div>

      <div className="mt-3 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-3">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Order history</p>
          <button
            type="button"
            onClick={clearOrders}
            className="rounded border border-[var(--nq-border)] px-2 py-0.5 text-[10px] text-[var(--nq-text-secondary)] hover:border-[var(--nq-border-hover)]"
          >
            Clear
          </button>
        </div>
        <div className="max-h-48 space-y-1 overflow-y-auto">
          {orders.slice(0, 25).map((order) => (
            <div key={order.transaction_id} className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-2 py-1.5 text-[10px] text-[var(--nq-text-secondary)]">
              <div className="flex items-center justify-between">
                <span className={order.type === "BUY" ? "text-[#00E676]" : "text-[#FF3B5C]"}>{order.type}</span>
                <span>{new Date(order.timestamp).toLocaleString()}</span>
              </div>
              <div className="mt-1 flex items-center justify-between">
                <span>{order.symbol}</span>
                <span>
                  {order.quantity.toLocaleString("en-IN", { maximumFractionDigits: 4 })} @ {order.price.toLocaleString("en-IN", { maximumFractionDigits: 4 })}
                </span>
              </div>
            </div>
          ))}
          {orders.length === 0 ? (
            <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-2 py-2 text-[10px] text-[var(--nq-text-secondary)]">
              No orders placed yet.
            </div>
          ) : null}
        </div>
      </div>

      <div className="mt-3 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">News feed</p>
        <div className="max-h-36 space-y-1 overflow-y-auto">
          {newsFeed.map((item, idx) => (
            <div key={`${item.headline}-${idx}`} className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-2 py-1.5 text-[10px]">
              <div className="flex items-center justify-between">
                <span className={item.sentiment === "POSITIVE" ? "text-[var(--nq-accent-green)]" : item.sentiment === "NEGATIVE" ? "text-[var(--nq-accent-red)]" : "text-[var(--nq-accent-amber)]"}>{item.sentiment}</span>
                <span className="text-[var(--nq-text-secondary)]">{item.time}</span>
              </div>
              <p className="mt-1 text-[var(--nq-text-secondary)]">{item.headline}</p>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
