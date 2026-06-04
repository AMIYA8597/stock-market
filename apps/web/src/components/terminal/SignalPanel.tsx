"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

import { SimpleDonutChart, type DonutSlice } from "@/components/charts";
import { useOrderHistory } from "@/hooks/use-order-history";
import { marketApi } from "@/lib/api-client";
import { contractsApi, type PortfolioTransactionRequest } from "@/lib/contracts-api";
import { safeFormat } from "@/lib/formatters";
import type { SignalResponse } from "@/types/intelligence";
import type { Quote } from "@neuroquant/types";

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
  const [mounted, setMounted] = useState<boolean>(false);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [quoteLoading, setQuoteLoading] = useState<boolean>(false);
  const [quoteError, setQuoteError] = useState<string | null>(null);
  const { orders, addOrder, clearOrders } = useOrderHistory();

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadQuote(): Promise<void> {
      if (!signal?.symbol) {
        setQuote(null);
        setQuoteError(null);
        setQuoteLoading(false);
        return;
      }

      setQuoteLoading(true);
      try {
        const liveQuote = await marketApi.getQuote(signal.symbol);
        if (cancelled) {
          return;
        }
        setQuote(liveQuote);
        setQuoteError(null);
      } catch (error) {
        if (cancelled) {
          return;
        }
        setQuote(null);
        setQuoteError(error instanceof Error ? error.message : "Live quote is unavailable.");
      } finally {
        if (!cancelled) {
          setQuoteLoading(false);
        }
      }
    }

    void loadQuote();

    return () => {
      cancelled = true;
    };
  }, [signal?.symbol]);

  const direction = signal?.ensemble.direction ?? "NEUTRAL";
  const confidence = signal ? safeFormat(Number(signal.ensemble.confidence) * 100, 1, "0.0") : "0.0";
  const featureRows = (signal?.models.xgboost.top_features ?? []).slice(0, 5);
  const latestPrice = quote?.price ?? null;

  useEffect(() => {
    if (latestPrice !== null && latestPrice > 0) {
      setPrice(safeFormat(latestPrice, 2, "0"));
    }
  }, [latestPrice]);

  useEffect(() => {
    const handleSetSide = (event: Event) => {
      const customEvent = event as CustomEvent;
      if (customEvent.detail) {
        setSide(customEvent.detail.side);
        const element = document.getElementById("order-ticket");
        if (element) {
          element.scrollIntoView({ behavior: "smooth" });
        }
      }
    };

    const handlePrefill = (event: Event) => {
      const customEvent = event as CustomEvent;
      if (customEvent.detail) {
        if (customEvent.detail.side) {
          setSide(customEvent.detail.side);
        }
        if (customEvent.detail.price) {
          setPrice(customEvent.detail.price.toString());
        }
        if (customEvent.detail.quantity) {
          setQuantity(customEvent.detail.quantity.toString());
        }
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

  const quoteChangePercent = quote ? safeFormat(quote.change_percent, 2, "0.00") : "--";
  const quoteRows = useMemo(
    () => [
      { label: "Last", value: latestPrice !== null ? safeFormat(latestPrice, 2) : "--" },
      { label: "Change", value: quote ? `${safeFormat(quote.change, 2)} (${quoteChangePercent}%)` : "--" },
      { label: "Open", value: quote ? safeFormat(quote.open, 2) : "--" },
      { label: "Prev Close", value: quote ? safeFormat(quote.previous_close, 2) : "--" },
      { label: "High", value: quote ? safeFormat(quote.high, 2) : "--" },
      { label: "Low", value: quote ? safeFormat(quote.low, 2) : "--" },
      { label: "Volume", value: quote ? quote.volume.toLocaleString("en-IN") : "--" },
      { label: "Quote Time", value: quote && mounted ? new Date(quote.timestamp).toLocaleTimeString() : "--:--:--" },
    ],
    [latestPrice, mounted, quote, quoteChangePercent]
  );

  const feedStatus = useMemo(
    () => [
      {
        label: "Signal engine",
        value: signal ? `${direction} @ ${confidence}% confidence` : "Waiting for signal feed",
      },
      {
        label: "Quote feed",
        value: quoteLoading
          ? "Refreshing live quote..."
          : quoteError
            ? "Unavailable"
            : quote
              ? "Connected"
              : "Idle",
      },
      {
        label: "Level 2 depth",
        value: "Not available from the current free provider stack",
      },
      {
        label: "News stream",
        value: "Not configured yet",
      },
    ],
    [confidence, direction, quote, quoteError, quoteLoading, signal]
  );

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
            <text x="40" y="44" textAnchor="middle" fontSize="11" fill="var(--nq-text-primary)" fontWeight="bold">
              {safeFormat(confidenceStroke, 0)}%
            </text>
          </svg>
          <div className="text-[11px] text-[var(--nq-text-secondary)]">
            <p className="font-mono">Kelly: {safeFormat(signal?.ensemble.kelly_fraction, 3, "0.000")}</p>
            <p className="mt-1">Active engines: {signal ? Object.keys(signal.model_weights).length : 0}</p>
          </div>
        </div>
      </div>

      <div className="mb-3 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Model breakdown</p>
        <div className="space-y-1.5 text-xs text-[var(--nq-text-secondary)]">
          {([
            ["tft", `TFT P10 ${safeFormat(signal?.models?.tft?.p10, 2)} | P50 ${safeFormat(signal?.models?.tft?.p50, 2)} | P90 ${safeFormat(signal?.models?.tft?.p90, 2)}`],
            ["hmm_garch", `HMM ${signal?.models?.hmm_garch?.regime_signal ?? "-"} | Vol 1d ${safeFormat(signal?.models?.hmm_garch?.vol_forecast_1d, 4, "0.0000")}`],
            ["gnn", `GNN spillover ${safeFormat(signal?.models?.gnn?.spillover_risk, 3, "0.000")} | Correlated: ${(signal?.models?.gnn?.top_correlated_assets ?? []).slice(0, 2).join(", ") || "--"}`],
            ["lstm_attn", `LSTM signal ${safeFormat(signal?.models?.lstm_attn?.raw_signal, 3, "0.000")}`],
            ["xgboost", `XGBoost raw ${safeFormat(signal?.models?.xgboost?.raw_signal, 3, "0.000")} | SHAP: ${(signal?.models?.xgboost?.top_features ?? []).slice(0, 2).map((feature) => String(feature.name)).join(", ") || "--"}`],
          ] as const).map(([key, summary]) => (
            <div key={key} className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.005)]">
              <button
                type="button"
                onClick={() => setExpandedModel(key)}
                className="flex w-full items-center justify-between px-2.5 py-1.5 text-left font-mono font-semibold"
              >
                <span className="uppercase text-[var(--nq-text-primary)]">{key}</span>
                <span>{expandedModel === key ? "-" : "+"}</span>
              </button>
              {expandedModel === key ? (
                <p className="border-t border-[var(--nq-border)] bg-[rgba(255,255,255,0.015)] px-2.5 py-2 text-[10px] font-mono leading-relaxed">
                  {summary}
                </p>
              ) : null}
            </div>
          ))}
        </div>
      </div>

      <div className="mb-3 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Live Quote Snapshot</p>
          <span className="text-[10px] font-mono text-[var(--nq-text-secondary)]">
            {quoteLoading ? "Refreshing..." : quote ? "Live quote loaded" : "Quote unavailable"}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
          {quoteRows.map((row) => (
            <div key={row.label} className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.015)] px-2 py-1.5">
              <p className="text-[9px] uppercase tracking-wider text-[var(--nq-text-secondary)]">{row.label}</p>
              <p className="mt-1 text-[var(--nq-text-primary)]">{row.value}</p>
            </div>
          ))}
        </div>
        {quoteError ? (
          <div className="mt-3 rounded border border-[rgba(255,59,92,0.35)] bg-[rgba(255,59,92,0.08)] px-2 py-1.5 text-[10px] text-[var(--nq-accent-red)]">
            Quote feed error: {quoteError}
          </div>
        ) : null}
      </div>

      <div className="mb-3 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Ensemble weight distribution</p>
        <div className="h-[140px]">
          <SimpleDonutChart
            data={weightSlices.length > 0 ? weightSlices : [{ name: "No Data", value: 1, color: "var(--nq-border)" }]}
            centerLabel="weights"
          />
        </div>
      </div>

      <div className="mb-3 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">XGBoost top features</p>
        <div className="space-y-1 font-mono text-xs text-[var(--nq-text-secondary)]">
          {featureRows.map((feature) => (
            <div key={String(feature.name)} className="flex justify-between rounded px-1 transition-colors hover:bg-[rgba(255,255,255,0.03)]">
              <span>{String(feature.name)}</span>
              <span>{safeFormat(feature.shap_value, 4)}</span>
            </div>
          ))}
          {featureRows.length === 0 ? (
            <div className="rounded bg-[rgba(255,255,255,0.03)] px-2 py-1 text-[10px]">No feature attribution received yet.</div>
          ) : null}
        </div>
      </div>

      <div id="order-ticket" className="mt-3 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3 shadow-md">
        <p className="mb-2 text-xs font-bold uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Order ticket</p>
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

          <label className="block text-[10px] font-semibold uppercase text-[var(--nq-text-secondary)]">
            Symbol
            <input
              type="text"
              readOnly
              value={signal?.symbol ?? ""}
              className="mt-1 w-full rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-2.5 py-1.5 font-mono text-xs text-[var(--nq-text-primary)] outline-none"
            />
          </label>

          <div className="grid grid-cols-2 gap-2 font-mono">
            <label className="block text-[10px] font-semibold uppercase text-[var(--nq-text-secondary)]">
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
            <label className="block text-[10px] font-semibold uppercase text-[var(--nq-text-secondary)]">
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

          <div className="flex justify-between rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-2.5 py-1.5 font-mono text-[10px] text-[var(--nq-text-secondary)]">
            <span>Notional Value:</span>
            <span className="font-bold text-[var(--nq-text-primary)]">
              INR {Number.isFinite(notional) ? notional.toLocaleString("en-IN", { maximumFractionDigits: 2 }) : "--"}
            </span>
          </div>

          {tradeError ? <p className="font-mono text-[10px] font-bold text-[#FF3B5C]">{tradeError}</p> : null}
          {tradeSuccess ? <p className="font-mono text-[10px] font-bold text-[#00E676]">{tradeSuccess}</p> : null}

          <button
            type="submit"
            disabled={submitting || !signal?.symbol}
            className={`w-full rounded px-3 py-2 text-xs font-bold uppercase tracking-wider text-black transition ${
              side === "BUY"
                ? "bg-[var(--accent-green)] shadow-[0_0_12px_rgba(0,230,118,0.3)] hover:bg-[#00c853]"
                : "bg-[var(--accent-red)] text-white shadow-[0_0_12px_rgba(255,59,92,0.3)] hover:bg-[#d50000]"
            } disabled:cursor-not-allowed disabled:opacity-50`}
          >
            {submitting ? "Placing order..." : `Place ${side} Order`}
          </button>
        </form>
      </div>

      <div className="mt-3 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3">
        <div className="mb-2 flex items-center justify-between border-b border-[var(--nq-border)] pb-1.5">
          <p className="text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Order history</p>
          <button
            type="button"
            onClick={clearOrders}
            className="rounded border border-[var(--nq-border)] px-2 py-0.5 text-[10px] font-semibold text-[var(--nq-text-secondary)] transition hover:bg-[rgba(255,255,255,0.05)]"
          >
            Clear
          </button>
        </div>
        <div className="max-h-48 space-y-1.5 overflow-y-auto ds-scrollable font-mono">
          {orders.slice(0, 25).map((order) => (
            <div
              key={order.transaction_id}
              className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] px-2.5 py-1.5 text-[10px] text-[var(--nq-text-secondary)]"
            >
              <div className="flex items-center justify-between">
                <span className={`font-bold ${order.type === "BUY" ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
                  {order.type}
                </span>
                <span className="text-[8px] opacity-75">
                  {mounted ? new Date(order.timestamp).toLocaleTimeString() : "--:--:--"}
                </span>
              </div>
              <div className="mt-1 flex items-center justify-between text-[var(--nq-text-primary)]">
                <span className="font-bold">{order.symbol}</span>
                <span>
                  {order.quantity.toLocaleString("en-IN", { maximumFractionDigits: 4 })} @ INR{" "}
                  {order.price.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                </span>
              </div>
            </div>
          ))}
          {orders.length === 0 ? (
            <div className="py-4 text-center text-[10px] text-[var(--nq-text-secondary)] opacity-60">No orders placed yet.</div>
          ) : null}
        </div>
      </div>

      <div className="mt-3 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3">
        <p className="mb-2 text-xs uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">Feed status</p>
        <div className="max-h-36 space-y-1.5 overflow-y-auto ds-scrollable font-mono">
          {feedStatus.map((item) => (
            <div
              key={item.label}
              className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.005)] px-2.5 py-1.5 text-[10px] leading-relaxed"
            >
              <div className="mb-1 flex items-center justify-between border-b border-[rgba(255,255,255,0.03)] pb-1">
                <span className="text-[8px] font-bold text-[var(--nq-accent-cyan)]">{item.label}</span>
                <span className="text-[8px] text-[var(--nq-text-secondary)] opacity-75">
                  {mounted ? new Date().toLocaleTimeString() : "--:--:--"}
                </span>
              </div>
              <p className="text-[var(--nq-text-secondary)]">{item.value}</p>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
