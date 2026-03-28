"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { contractsApi, type PortfolioTransactionRequest } from "@/lib/contracts-api";
import { useOrderHistory } from "@/hooks/use-order-history";
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
        <p className="mt-2 text-sm text-[var(--nq-text-secondary)]">
          Kelly {(signal?.ensemble.kelly_fraction ?? 0).toFixed(3)}
        </p>
      </div>

      <div className="mb-3 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Model details</p>
        <div className="grid grid-cols-2 gap-2 text-xs text-[var(--nq-text-secondary)]">
          <div className="rounded border border-[var(--nq-border)] px-2 py-1">TFT p50 {(signal?.models.tft.p50 ?? 0).toFixed(4)}</div>
          <div className="rounded border border-[var(--nq-border)] px-2 py-1">HMM {signal?.models.hmm_garch.regime_signal ?? "-"}</div>
          <div className="rounded border border-[var(--nq-border)] px-2 py-1">GNN {(signal?.models.gnn.spillover_risk ?? 0).toFixed(3)}</div>
          <div className="rounded border border-[var(--nq-border)] px-2 py-1">LSTM {(signal?.models.lstm_attn.raw_signal ?? 0).toFixed(3)}</div>
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
    </aside>
  );
}
