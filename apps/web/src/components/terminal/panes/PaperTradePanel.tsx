"use client";

import { useState, FormEvent } from "react";
import { usePriceFeed } from "@/hooks/usePriceFeed";
import { paperTradingApi } from "@/lib/api-client";

interface PaperTradePanelProps {
  selectedSymbol?: string;
}

export default function PaperTradePanel({ selectedSymbol }: PaperTradePanelProps): JSX.Element {
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [quantity, setQuantity] = useState<string>("10");
  const [orderType, setOrderType] = useState<"MARKET" | "LIMIT">("MARKET");
  const [price, setPrice] = useState<string>("0");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: "error" | "success"; text: string } | null>(null);

  const { ticks } = usePriceFeed(selectedSymbol ? [selectedSymbol] : []);
  const liveTick = selectedSymbol ? ticks.get(selectedSymbol.toUpperCase()) : null;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedSymbol) {
      setMessage({ type: "error", text: "Please select a symbol from the watchlist first." });
      return;
    }

    const parsedQty = Number(quantity);
    if (!Number.isFinite(parsedQty) || parsedQty <= 0) {
      setMessage({ type: "error", text: "Quantity must be greater than zero." });
      return;
    }

    
    const parsedPrice = orderType === "MARKET" ? liveTick?.price : Number(price);
    if (orderType === "MARKET" && typeof parsedPrice !== "number") {
      setMessage({ type: "error", text: "Cannot place MARKET order: Live price unavailable." });
      return;
    }

    if (orderType === "LIMIT" && (!Number.isFinite(parsedPrice) || (parsedPrice as number) <= 0)) {
      setMessage({ type: "error", text: "Price must be greater than zero for LIMIT orders." });
      return;
    }

    setSubmitting(true);
    setMessage(null);

    try {
      await paperTradingApi.submitOrder({
        symbol: selectedSymbol,
        side,
        quantity: parsedQty,
        order_type: orderType,
        limit_price: orderType === "LIMIT" ? (parsedPrice as number) : undefined,
      });

      setMessage({ type: "success", text: `Successfully placed ${side} order for ${parsedQty} ${selectedSymbol}` });
      if (orderType === "LIMIT") {
        setPrice("0");
      }
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : "Failed to submit order";
      setMessage({ type: "error", text: errorMsg });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex h-full flex-col bg-[var(--bg-base)]">
      <div className="flex-1 overflow-y-auto p-4">
        <h3 className="mb-4 text-sm font-bold uppercase tracking-wider text-[var(--text-primary)]">
          Paper Trade
        </h3>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-1">
            <button
              type="button"
              onClick={() => setSide("BUY")}
              className={`flex-1 rounded py-2.5 md:py-1.5 min-h-[44px] md:min-h-0 text-xs font-bold transition-all ${
                side === "BUY" ? "bg-[rgba(0,230,118,0.15)] text-[var(--accent-green)]" : "text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
              }`}
            >
              BUY
            </button>
            <button
              type="button"
              onClick={() => setSide("SELL")}
              className={`flex-1 rounded py-2.5 md:py-1.5 min-h-[44px] md:min-h-0 text-xs font-bold transition-all ${
                side === "SELL" ? "bg-[rgba(255,59,92,0.15)] text-[var(--accent-red)]" : "text-[var(--text-secondary)] hover:bg-[var(--bg-hover)]"
              }`}
            >
              SELL
            </button>
          </div>

          <div className="flex gap-4">
            <div className="flex-1">
              <label className="mb-1 block text-[10px] uppercase text-[var(--text-tertiary)]">Type</label>
              <select
                value={orderType}
                onChange={(e) => setOrderType(e.target.value as "MARKET" | "LIMIT")}
                className="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2 py-2.5 md:py-1.5 min-h-[44px] md:min-h-0 text-sm text-[var(--text-primary)] focus:border-[var(--accent-cyan)] focus:outline-none"
              >
                <option value="MARKET">Market</option>
                <option value="LIMIT">Limit</option>
              </select>
            </div>
            <div className="flex-1">
              <label className="mb-1 block text-[10px] uppercase text-[var(--text-tertiary)]">Quantity</label>
              <input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                min="1"
                className="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2 py-2.5 md:py-1.5 min-h-[44px] md:min-h-0 text-sm text-[var(--text-primary)] focus:border-[var(--accent-cyan)] focus:outline-none"
              />
            </div>
          </div>

          {orderType === "LIMIT" && (
            <div>
              <label className="mb-1 block text-[10px] uppercase text-[var(--text-tertiary)]">Limit Price</label>
              <input
                type="number"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                step="0.05"
                min="0"
                className="w-full rounded border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-2 py-2.5 md:py-1.5 min-h-[44px] md:min-h-0 text-sm text-[var(--text-primary)] focus:border-[var(--accent-cyan)] focus:outline-none"
              />
            </div>
          )}

          <div className="mt-2 text-xs text-[var(--text-secondary)]">
            Est. Value: { (orderType === "MARKET" && typeof liveTick?.price === "number" || orderType === "LIMIT" && Number(price) > 0) ? `₹${(((orderType === "MARKET" ? liveTick!.price! : Number(price)) * Number(quantity)) || 0).toLocaleString()}` : "N/A" }
          </div>

          <button
            type="submit"
            disabled={submitting || !selectedSymbol}
            className={`mt-4 w-full rounded py-2.5 text-sm font-bold transition-all ${
              !selectedSymbol
                ? "bg-[var(--bg-surface)] text-[var(--text-tertiary)] cursor-not-allowed border border-[var(--border-subtle)]"
                : side === "BUY"
                ? "bg-[var(--accent-green)] text-[#000] hover:bg-[#00c853]"
                : "bg-[var(--accent-red)] text-[#fff] hover:bg-[#d50000]"
            } ${submitting ? "opacity-75" : ""}`}
          >
            {submitting ? "Submitting..." : `${side} ${selectedSymbol || ""}`}
          </button>

          {message && (
            <div className={`mt-2 rounded p-2 text-xs font-medium ${message.type === "success" ? "bg-[rgba(0,230,118,0.1)] text-[var(--accent-green)] border border-[rgba(0,230,118,0.2)]" : "bg-[rgba(255,59,92,0.1)] text-[var(--accent-red)] border border-[rgba(255,59,92,0.2)]"}`}>
              {message.text}
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
