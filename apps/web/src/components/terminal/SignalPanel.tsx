"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { contractsApi, type PortfolioTransactionRequest } from "@/lib/contracts-api";
import { useOrderHistory } from "@/hooks/use-order-history";
import { SimpleDonutChart, type DonutSlice } from "@/components/charts";
import { safeFormat } from "@/lib/formatters";
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
  const [mounted, setMounted] = useState<boolean>(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const direction = signal?.ensemble.direction ?? "NEUTRAL";
  const confidence = signal ? safeFormat(Number(signal.ensemble.confidence) * 100, 1, "0.0") : "0.0";
  const featureRows = (signal?.models.xgboost.top_features ?? []).slice(0, 5);
  
  const latestPrice = useMemo(() => {
    const median = signal?.models?.tft?.p50;
    if (typeof median === "number" && Number.isFinite(median) && median > 0) {
      return median;
    }
    return 100.0;
  }, [signal?.models?.tft?.p50]);

  // Order Book / L2 Market Depth state & simulation (Zerodha style)
  const [depthOffset, setDepthOffset] = useState<number>(0);

  useEffect(() => {
    const id = setInterval(() => {
      setDepthOffset((prev) => prev + (Math.random() - 0.5) * 0.04);
    }, 4000);
    return () => clearInterval(id);
  }, []);

  const marketDepth = useMemo(() => {
    const base = latestPrice;
    
    // Seed bids (buyers at slightly lower prices)
    const bidOffsets = [0.05, 0.10, 0.15, 0.20, 0.25];
    const bids = bidOffsets.map((offset, idx) => {
      const p = base - offset + depthOffset;
      const seed = Math.abs(Math.sin(p + idx)) * 1000;
      const qty = Math.round((250 + (seed % 650)) / 5) * 5;
      const ords = Math.max(1, Math.round(qty / 150 + (qty % 4)));
      return { price: p, qty, orders: ords };
    });

    // Seed asks (sellers at slightly higher prices)
    const askOffsets = [0.05, 0.10, 0.15, 0.20, 0.25];
    const asks = askOffsets.map((offset, idx) => {
      const p = base + offset + depthOffset;
      const seed = Math.abs(Math.cos(p + idx)) * 1000;
      const qty = Math.round((200 + (seed % 600)) / 5) * 5;
      const ords = Math.max(1, Math.round(qty / 120 + (qty % 3)));
      return { price: p, qty, orders: ords };
    });

    const totalBidQty = bids.reduce((sum, b) => sum + b.qty, 0);
    const totalAskQty = asks.reduce((sum, a) => sum + a.qty, 0);
    const totalQty = totalBidQty + totalAskQty || 1;
    const bidPercent = Math.round((totalBidQty / totalQty) * 100);
    const askPercent = 100 - bidPercent;

    return { bids, asks, totalBidQty, totalAskQty, bidPercent, askPercent };
  }, [latestPrice, depthOffset]);

  // Listen to select-order-side and prefill-order-ticket custom events
  useEffect(() => {
    const handleSetSide = (e: Event) => {
      const customEvent = e as CustomEvent;
      if (customEvent.detail) {
        setSide(customEvent.detail.side);
        const element = document.getElementById("order-ticket");
        if (element) {
          element.scrollIntoView({ behavior: "smooth" });
        }
      }
    };

    const handlePrefill = (e: Event) => {
      const customEvent = e as CustomEvent;
      if (customEvent.detail) {
        if (customEvent.detail.side) setSide(customEvent.detail.side);
        if (customEvent.detail.price) setPrice(customEvent.detail.price.toString());
        if (customEvent.detail.quantity) setQuantity(customEvent.detail.quantity.toString());
        const element = document.getElementById("order-ticket");
        if (element) {
          element.scrollIntoView({ behavior: "smooth" });
        }
      }
    };

    window.addEventListener("select-order-side", handleSetSide);
    window.addEventListener("prefill-order-ticket", handlePrefill);
    return () => {
      window.removeEventListener("select-order-side", handleSetSide);
      window.removeEventListener("prefill-order-ticket", handlePrefill);
    };
  }, []);

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

  const [newsFeed, setNewsFeed] = useState<Array<{ headline: string; sentiment: string; time: string }>>([]);

  useEffect(() => {
    const currentSymbol = signal?.symbol ?? "MARKET";
    const directionBias = signal?.ensemble.direction ?? "NEUTRAL";
    const now = new Date();
    setNewsFeed([
      { headline: `${currentSymbol} guidance updates market expectations`, sentiment: "POSITIVE", time: now.toLocaleTimeString() },
      { headline: `Regime shift monitor flags ${currentSymbol} as ${directionBias}`, sentiment: directionBias.includes("SELL") ? "NEGATIVE" : "NEUTRAL", time: new Date(now.getTime() - 12 * 60_000).toLocaleTimeString() },
      { headline: `Cross-asset flow indicates volatility clustering in ${currentSymbol}`, sentiment: "NEUTRAL", time: new Date(now.getTime() - 28 * 60_000).toLocaleTimeString() },
    ]);
  }, [signal?.ensemble.direction, signal?.symbol]);

  useEffect(() => {
    if (latestPrice > 0) {
      setPrice(safeFormat(latestPrice, 2, "0"));
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
    <aside className="h-full overflow-y-auto border-t border-[var(--nq-border)] bg-[var(--nq-bg-surface)] p-3 lg:border-l lg:border-t-0 ds-scrollable ds-page-transition">
      {/* Ensemble Header */}
      <div className="mb-3 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Ensemble signal</p>
        <span className={`inline-flex rounded border px-2 py-1 text-xs font-semibold ${badgeStyles[direction]}`}>
          {direction}
        </span>
        <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
          <p className="rounded bg-[rgba(255,255,255,0.03)] px-2 py-1 text-[var(--nq-text-secondary)]">Confidence {confidence}%</p>
          <p className="rounded bg-[rgba(255,255,255,0.03)] px-2 py-1 text-[var(--nq-text-secondary)]">Regime {signal?.regime.state ?? "-"}</p>
        </div>
        <div className="mt-2 grid grid-cols-[80px_1fr] items-center gap-3">
          <svg viewBox="0 0 80 80" className="h-16 w-16" aria-label="Confidence gauge">
            <circle cx="40" cy="40" r="34" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="6" />
            <circle
              cx="40"
              cy="40"
              r="34"
              fill="none"
              stroke="var(--nq-accent-cyan)"
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={gaugeCircumference}
              strokeDashoffset={gaugeOffset}
              transform="rotate(-90 40 40)"
            />
            <text x="40" y="44" textAnchor="middle" fontSize="11" fill="var(--nq-text-primary)" fontWeight="bold">{safeFormat(confidenceStroke, 0)}%</text>
          </svg>
          <div className="text-[11px] text-[var(--nq-text-secondary)]">
            <p className="font-mono">Kelly: {safeFormat(signal?.ensemble.kelly_fraction, 3, "0.000")}</p>
            <p className="mt-1">Active engines: {signal ? Object.keys(signal.model_weights).length : 0}</p>
          </div>
        </div>
      </div>

      {/* Model breakdown */}
      <div className="mb-3 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Model breakdown</p>
        <div className="space-y-1.5 text-xs text-[var(--nq-text-secondary)]">
          {([
            ["tft", `TFT P10 ${safeFormat(signal?.models?.tft?.p10, 2)} | P50 ${safeFormat(signal?.models?.tft?.p50, 2)} | P90 ${safeFormat(signal?.models?.tft?.p90, 2)}`],
            ["hmm_garch", `HMM ${signal?.models?.hmm_garch?.regime_signal ?? "-"} | Vol 1d ${safeFormat(signal?.models?.hmm_garch?.vol_forecast_1d, 4, "0.0000")}`],
            ["gnn", `GNN spillover ${safeFormat(signal?.models?.gnn?.spillover_risk, 3, "0.000")} | Correlated: ${(signal?.models?.gnn?.top_correlated_assets ?? []).slice(0, 2).join(", ") || "--"}`],
            ["lstm_attn", `LSTM signal ${safeFormat(signal?.models?.lstm_attn?.raw_signal, 3, "0.000")}`],
            ["xgboost", `XGBoost raw ${safeFormat(signal?.models?.xgboost?.raw_signal, 3, "0.000")} | SHAP: ${(signal?.models?.xgboost?.top_features ?? []).slice(0, 2).map((f) => String(f.name)).join(", ") || "--"}`],
          ] as const).map(([key, summary]) => (
            <div key={key} className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.005)]">
              <button
                type="button"
                onClick={() => setExpandedModel(key)}
                className="flex w-full items-center justify-between px-2.5 py-1.5 text-left font-mono font-semibold"
              >
                <span className="uppercase text-[var(--nq-text-primary)]">{key}</span>
                <span>{expandedModel === key ? "−" : "+"}</span>
              </button>
              {expandedModel === key ? (
                <p className="border-t border-[var(--nq-border)] bg-[rgba(255,255,255,0.015)] px-2.5 py-2 text-[10px] leading-relaxed font-mono">
                  {summary}
                </p>
              ) : null}
            </div>
          ))}
        </div>
      </div>

      {/* L2 Market Depth (Zerodha style) */}
      <div className="mb-3 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Market Depth (L2)</p>
        
        <div className="grid grid-cols-2 gap-x-3 text-[10px] font-mono">
          {/* Bids */}
          <div>
            <div className="flex justify-between border-b border-[var(--nq-border)] pb-1 text-[9px] uppercase tracking-wider text-[var(--nq-text-secondary)] font-bold">
              <span>Bid Price</span>
              <span>Qty</span>
              <span>Orders</span>
            </div>
            <div className="space-y-1 mt-1 text-[var(--accent-green)]">
              {marketDepth.bids.map((b, idx) => (
                <div key={idx} className="flex justify-between hover:bg-[rgba(0,230,118,0.05)] px-0.5 rounded">
                  <span>{safeFormat(b.price, 2)}</span>
                  <span>{b.qty}</span>
                  <span className="text-[var(--nq-text-secondary)]">{b.orders}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Asks */}
          <div>
            <div className="flex justify-between border-b border-[var(--nq-border)] pb-1 text-[9px] uppercase tracking-wider text-[var(--nq-text-secondary)] font-bold">
              <span>Ask Price</span>
              <span>Qty</span>
              <span>Orders</span>
            </div>
            <div className="space-y-1 mt-1 text-[var(--accent-red)]">
              {marketDepth.asks.map((a, idx) => (
                <div key={idx} className="flex justify-between hover:bg-[rgba(255,59,92,0.05)] px-0.5 rounded">
                  <span>{safeFormat(a.price, 2)}</span>
                  <span>{a.qty}</span>
                  <span className="text-[var(--nq-text-secondary)]">{a.orders}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Total Volumes & Ratio Bar */}
        <div className="mt-3 border-t border-[var(--nq-border)] pt-2 text-[10px] font-mono">
          <div className="flex justify-between text-[var(--nq-text-secondary)] mb-1">
            <span>Total Bid: <strong className="text-[var(--accent-green)]">{marketDepth.totalBidQty}</strong></span>
            <span>Total Ask: <strong className="text-[var(--accent-red)]">{marketDepth.totalAskQty}</strong></span>
          </div>
          <div className="relative h-2 w-full overflow-hidden rounded bg-[rgba(255,255,255,0.08)] flex">
            <div
              style={{ width: `${marketDepth.bidPercent}%` }}
              className="h-full bg-[var(--accent-green)] transition-all duration-300"
            />
            <div
              style={{ width: `${marketDepth.askPercent}%` }}
              className="h-full bg-[var(--accent-red)] transition-all duration-300"
            />
          </div>
          <div className="flex justify-between text-[8px] text-[var(--nq-text-secondary)] mt-1 font-semibold">
            <span>{marketDepth.bidPercent}% BUYERS</span>
            <span>{marketDepth.askPercent}% SELLERS</span>
          </div>
        </div>
      </div>

      {/* EnsembleWeightPie */}
      <div className="mb-3 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Ensemble weight distribution</p>
        <div className="h-[140px]">
          <SimpleDonutChart data={weightSlices.length > 0 ? weightSlices : [{ name: "No Data", value: 1, color: "var(--nq-border)" }]} centerLabel="weights" />
        </div>
      </div>

      {/* XGBoost top features */}
      <div className="mb-3 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">XGBoost top features</p>
        <div className="space-y-1 text-xs text-[var(--nq-text-secondary)] font-mono">
          {featureRows.map((feature) => (
            <div key={String(feature.name)} className="flex justify-between hover:bg-[rgba(255,255,255,0.03)] px-1 rounded transition-colors">
              <span>{String(feature.name)}</span>
              <span>{safeFormat(feature.shap_value, 4)}</span>
            </div>
          ))}
          {featureRows.length === 0 ? <div className="rounded bg-[rgba(255,255,255,0.03)] px-2 py-1 text-[10px]">No feature attribution received yet.</div> : null}
        </div>
      </div>

      {/* Order ticket */}
      <div id="order-ticket" className="mt-3 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3 shadow-md">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)] font-bold">Order ticket</p>
        <form className="space-y-2.5" onSubmit={submitOrder}>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <button
              type="button"
              onClick={() => setSide("BUY")}
              className={`rounded border px-2 py-1.5 font-bold uppercase transition ${
                side === "BUY"
                  ? "border-[#00E676] bg-[rgba(0,230,118,0.15)] text-[#00E676]"
                  : "border-[var(--nq-border)] text-[var(--nq-text-secondary)] hover:border-[var(--nq-border-hover)]"
              }`}
            >
              Buy
            </button>
            <button
              type="button"
              onClick={() => setSide("SELL")}
              className={`rounded border px-2 py-1.5 font-bold uppercase transition ${
                side === "SELL"
                  ? "border-[#FF3B5C] bg-[rgba(255,59,92,0.15)] text-[#FF3B5C]"
                  : "border-[var(--nq-border)] text-[var(--nq-text-secondary)] hover:border-[var(--nq-border-hover)]"
              }`}
            >
              Sell
            </button>
          </div>

          <label className="block text-[10px] uppercase text-[var(--nq-text-secondary)] font-semibold">
            Symbol
            <input
              type="text"
              readOnly
              value={signal?.symbol ?? ""}
              className="mt-1 w-full rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-2.5 py-1.5 text-xs text-[var(--nq-text-primary)] outline-none font-mono"
            />
          </label>

          <div className="grid grid-cols-2 gap-2 font-mono">
            <label className="block text-[10px] uppercase text-[var(--nq-text-secondary)] font-semibold">
              Quantity
              <input
                type="number"
                min="0.0001"
                step="0.0001"
                value={quantity}
                onChange={(event) => setQuantity(event.target.value)}
                className="mt-1 w-full rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-2.5 py-1.5 text-xs text-[var(--nq-text-primary)] outline-none focus:border-[var(--nq-accent)]"
              />
            </label>
            <label className="block text-[10px] uppercase text-[var(--nq-text-secondary)] font-semibold">
              Price (INR)
              <input
                type="number"
                min="0.0001"
                step="0.0001"
                value={price}
                onChange={(event) => setPrice(event.target.value)}
                className="mt-1 w-full rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-2.5 py-1.5 text-xs text-[var(--nq-text-primary)] outline-none focus:border-[var(--nq-accent)]"
              />
            </label>
          </div>

          <div className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-2.5 py-1.5 text-[10px] text-[var(--nq-text-secondary)] font-mono flex justify-between">
            <span>Notional Value:</span>
            <span className="font-bold text-[var(--nq-text-primary)]">
              ₹{Number.isFinite(notional) ? notional.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : "--"}
            </span>
          </div>

          {tradeError ? <p className="text-[10px] font-bold text-[#FF3B5C] font-mono">{tradeError}</p> : null}
          {tradeSuccess ? <p className="text-[10px] font-bold text-[#00E676] font-mono">{tradeSuccess}</p> : null}

          <button
            type="submit"
            disabled={submitting || !signal?.symbol}
            className={`w-full rounded px-3 py-2 text-xs font-bold text-black transition uppercase tracking-wider ${
              side === "BUY"
                ? "bg-[var(--accent-green)] hover:bg-[#00c853] shadow-[0_0_12px_rgba(0,230,118,0.3)]"
                : "bg-[var(--accent-red)] hover:bg-[#d50000] text-white shadow-[0_0_12px_rgba(255,59,92,0.3)]"
            } disabled:cursor-not-allowed disabled:opacity-50`}
          >
            {submitting ? "Placing order..." : `Place ${side} Order`}
          </button>
        </form>
      </div>

      {/* Order history */}
      <div className="mt-3 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3">
        <div className="mb-2 flex items-center justify-between border-b border-[var(--nq-border)] pb-1.5">
          <p className="text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Order history</p>
          <button
            type="button"
            onClick={clearOrders}
            className="rounded border border-[var(--nq-border)] px-2 py-0.5 text-[10px] text-[var(--nq-text-secondary)] hover:bg-[rgba(255,255,255,0.05)] font-semibold transition"
          >
            Clear
          </button>
        </div>
        <div className="max-h-48 space-y-1.5 overflow-y-auto ds-scrollable font-mono">
          {orders.slice(0, 25).map((order) => (
            <div key={order.transaction_id} className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] px-2.5 py-1.5 text-[10px] text-[var(--nq-text-secondary)]">
              <div className="flex items-center justify-between">
                <span className={`font-bold ${order.type === "BUY" ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
                  {order.type}
                </span>
                <span className="text-[8px] opacity-75">{mounted ? new Date(order.timestamp).toLocaleTimeString() : "--:--:--"}</span>
              </div>
              <div className="mt-1 flex items-center justify-between text-[var(--nq-text-primary)]">
                <span className="font-bold">{order.symbol}</span>
                <span>
                  {order.quantity.toLocaleString("en-IN", { maximumFractionDigits: 4 })} @ ₹{order.price.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                </span>
              </div>
            </div>
          ))}
          {orders.length === 0 ? (
            <div className="py-4 text-center text-[10px] text-[var(--nq-text-secondary)] opacity-60">
              No orders placed yet.
            </div>
          ) : null}
        </div>
      </div>

      {/* News feed */}
      <div className="mt-3 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">News feed</p>
        <div className="max-h-36 space-y-1.5 overflow-y-auto ds-scrollable font-mono">
          {newsFeed.map((item, idx) => (
            <div key={`${item.headline}-${idx}`} className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.005)] px-2.5 py-1.5 text-[10px] leading-relaxed">
              <div className="flex items-center justify-between border-b border-[rgba(255,255,255,0.03)] pb-1 mb-1">
                <span className={`text-[8px] font-bold ${item.sentiment === "POSITIVE" ? "text-[var(--nq-accent-green)]" : item.sentiment === "NEGATIVE" ? "text-[var(--nq-accent-red)]" : "text-[var(--nq-accent-amber)]"}`}>{item.sentiment}</span>
                <span className="text-[8px] text-[var(--nq-text-secondary)] opacity-75">{mounted ? item.time : "--:--:--"}</span>
              </div>
              <p className="text-[var(--nq-text-secondary)]">{item.headline}</p>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
