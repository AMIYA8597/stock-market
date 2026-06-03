"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { contractsApi, type PortfolioHolding, type PortfolioPerformancePoint, type PortfolioRiskMetrics, type JournalEntry } from "@/lib/contracts-api";
import { usePriceFeed } from "@/hooks/usePriceFeed";

const CURRENCY_FORMATTER = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 2,
  minimumFractionDigits: 2,
});

const PERCENT_FORMATTER = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 2,
  minimumFractionDigits: 2,
});

function formatMoney(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return `₹${CURRENCY_FORMATTER.format(value)}`;
}

function formatPct(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return `${value >= 0 ? "+" : ""}${PERCENT_FORMATTER.format(value)}%`;
}



export default function PortfolioPage(): JSX.Element {
  const [holdings, setHoldings] = useState<PortfolioHolding[]>([]);
  const [risk, setRisk] = useState<PortfolioRiskMetrics | null>(null);
  const [performance, setPerformance] = useState<PortfolioPerformancePoint[]>([]);
  const [totalReturn, setTotalReturn] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Tabs state
  const [activeTab, setActiveTab] = useState<"holdings" | "positions" | "journal">("holdings");

  // Journal entries state
  const [journals, setJournals] = useState<JournalEntry[]>([]);
  
  // Journal Form Inputs
  const [jsym, setJsym] = useState("");
  const [jnotes, setJnotes] = useState("");
  const [jtags, setJtags] = useState("");
  const [jrating, setJrating] = useState(5);
  const [jentryPrice, setJentryPrice] = useState("");
  const [jexitPrice, setJexitPrice] = useState("");
  const [jqty, setJqty] = useState("");
  const [jdir, setJdir] = useState("LONG");
  const [journalSubmitting, setJournalSubmitting] = useState(false);
  const [journalError, setJournalError] = useState<string | null>(null);

  // Load portfolio data
  useEffect(() => {
    let mounted = true;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);
      const [holdingsRes, riskRes, perfRes] = await Promise.allSettled([
        contractsApi.getPortfolioHoldings(),
        contractsApi.getPortfolioRiskMetrics(),
        contractsApi.getPortfolioPerformance(),
      ]);

      if (!mounted) return;

      if (holdingsRes.status === "fulfilled") {
        setHoldings(holdingsRes.value.holdings);
      } else {
        setError("Unable to load portfolio holdings contract.");
      }

      if (riskRes.status === "fulfilled") {
        setRisk(riskRes.value);
      }

      if (perfRes.status === "fulfilled") {
        setPerformance(perfRes.value.series);
        setTotalReturn(perfRes.value.total_return);
      }

      setLoading(false);
    }

    void load();

    return () => {
      mounted = false;
    };
  }, []);

  // Load journals list
  const loadJournals = async () => {
    try {
      const data = await contractsApi.getJournals();
      setJournals(data);
    } catch (e) {
      console.error("Error loading journals:", e);
    }
  };

  useEffect(() => {
    void loadJournals();
  }, []);

  // Setup live prices via websocket
  const symbols = useMemo(() => holdings.map((h) => h.symbol.toUpperCase()), [holdings]);
  const { ticks, status } = usePriceFeed(symbols);

  // Calculate live valuations
  const portfolioValue = useMemo(() => {
    return holdings.reduce((sum, holding) => {
      const livePrice = ticks.get(holding.symbol.toUpperCase())?.price ?? holding.ltp;
      return sum + livePrice * holding.quantity;
    }, 0);
  }, [holdings, ticks]);

  const totalUnrealized = useMemo(() => {
    return holdings.reduce((sum, holding) => {
      const livePrice = ticks.get(holding.symbol.toUpperCase())?.price ?? holding.ltp;
      return sum + (livePrice - holding.avg_buy_price) * holding.quantity;
    }, 0);
  }, [holdings, ticks]);

  const performanceBars = useMemo(() => {
    const values = performance.slice(-120).map((point) => point.portfolio_value);
    if (values.length === 0) return [] as number[];
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = Math.max(max - min, 1e-9);
    return values.map((value) => 8 + ((value - min) / range) * 84);
  }, [performance]);

  // Mock active positions data matching professional derivatives/MIS interface
  const positions = useMemo(() => {
    return [
      { symbol: "RELIANCE.NS", product: "MIS", qty: 25, avgPrice: 2420.50, realized: 450, isIntraday: true },
      { symbol: "NIFTY26JUN22000CE", product: "NRML", qty: 150, avgPrice: 120.40, realized: -1200, isIntraday: false },
      { symbol: "BTC-USD", product: "MIS", qty: 0.15, avgPrice: 67200.00, realized: 0, isIntraday: true },
    ].map(pos => {
      const livePrice = ticks.get(pos.symbol.toUpperCase())?.price ?? (pos.symbol === "BTC-USD" ? 67850 : 2435.50);
      const unrealized = pos.qty > 0 ? (livePrice - pos.avgPrice) * pos.qty : 0;
      return {
        ...pos,
        ltp: livePrice,
        unrealized,
        totalPnl: pos.realized + unrealized,
      };
    });
  }, [ticks]);

  // Handle new journal log submission
  const handleSubmitJournal = async (e: React.FormEvent) => {
    e.preventDefault();
    setJournalError(null);
    if (!jsym.trim()) {
      setJournalError("Ticker is required.");
      return;
    }
    if (!jnotes.trim()) {
      setJournalError("Log review notes are required.");
      return;
    }

    setJournalSubmitting(true);
    try {
      const payload = {
        symbol: jsym,
        notes: jnotes,
        tags: jtags || null,
        rating: jrating,
        entry_price: jentryPrice ? parseFloat(jentryPrice) : null,
        exit_price: jexitPrice ? parseFloat(jexitPrice) : null,
        quantity: jqty ? parseFloat(jqty) : null,
        direction: jdir || null,
      };

      await contractsApi.createJournal(payload);
      
      // Reset form
      setJsym("");
      setJnotes("");
      setJtags("");
      setJrating(5);
      setJentryPrice("");
      setJexitPrice("");
      setJqty("");
      
      // Reload list
      await loadJournals();
    } catch (err) {
      setJournalError("Failed to add entry. Please verify inputs.");
    } finally {
      setJournalSubmitting(false);
    }
  };

  // Handle delete journal entry
  const handleDeleteJournal = async (id: string) => {
    try {
      await contractsApi.deleteJournal(id);
      await loadJournals();
    } catch (e) {
      console.error("Error deleting journal entry:", e);
    }
  };

  return (
    <main className="min-h-screen bg-[var(--nq-bg-base)] p-6 text-[var(--nq-text-primary)]">
      <h1 className="mb-2 text-2xl font-semibold">Portfolio Workspace</h1>
      <div className="mb-4 flex items-center justify-between gap-3 flex-wrap">
        <p className="text-xs text-[var(--nq-text-secondary)]">
          Manage positions, holdings, and log strategy audits. Price feed status: {status}.
        </p>
        <div className="flex items-center gap-2">
          <Link
            href="/portfolio/funds"
            className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1.5 text-xs text-[var(--nq-text-secondary)] hover:border-[var(--nq-border-hover)]"
          >
            Add funds
          </Link>
          <Link
            href="/portfolio/orders"
            className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1.5 text-xs text-[var(--nq-text-secondary)] hover:border-[var(--nq-border-hover)]"
          >
            View order history
          </Link>
        </div>
      </div>
      {error ? <p className="mb-2 text-sm text-[var(--nq-accent-red)]">{error}</p> : null}

      {/* Overview Cards */}
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Portfolio Value", formatMoney(portfolioValue)],
          ["Unrealized PnL", formatMoney(totalUnrealized)],
          ["Total Return", formatPct(totalReturn)],
          ["Beta Score", typeof risk?.beta === "number" ? risk.beta.toFixed(2) : "--"],
        ].map(([key, value]) => (
          <div key={key} className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-4 py-3">
            <div className="text-xs text-[var(--nq-text-secondary)]">{key}</div>
            <div className="mt-1 text-sm font-semibold">{value}</div>
          </div>
        ))}
      </section>

      {/* Tabs Row */}
      <div className="mt-6 flex border-b border-[var(--nq-border)] gap-6 text-sm font-medium">
        <button
          onClick={() => setActiveTab("holdings")}
          className={`pb-2.5 transition border-b-2 ${
            activeTab === "holdings"
              ? "border-[var(--nq-accent-cyan)] text-[var(--nq-text-primary)]"
              : "border-transparent text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)]"
          }`}
        >
          Holdings ({holdings.length})
        </button>
        <button
          onClick={() => setActiveTab("positions")}
          className={`pb-2.5 transition border-b-2 ${
            activeTab === "positions"
              ? "border-[var(--nq-accent-cyan)] text-[var(--nq-text-primary)]"
              : "border-transparent text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)]"
          }`}
        >
          Active Positions ({positions.length})
        </button>
        <button
          onClick={() => setActiveTab("journal")}
          className={`pb-2.5 transition border-b-2 ${
            activeTab === "journal"
              ? "border-[var(--nq-accent-cyan)] text-[var(--nq-text-primary)]"
              : "border-transparent text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)]"
          }`}
        >
          Trade Journal ({journals.length})
        </button>
      </div>

      {/* Content Area */}
      <div className="mt-4">
        {/* HOLDINGS TAB */}
        {activeTab === "holdings" && (
          <div className="grid gap-4 xl:grid-cols-[2fr_1fr]">
            <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4 overflow-x-auto">
              <table className="min-w-full text-xs font-mono">
                <thead>
                  <tr className="text-[var(--nq-text-secondary)] border-b border-[var(--nq-border)] pb-2 text-[10px] uppercase">
                    <th className="pb-2 text-left font-semibold">Ticker</th>
                    <th className="pb-2 text-right font-semibold">Quantity</th>
                    <th className="pb-2 text-right font-semibold">Avg Price</th>
                    <th className="pb-2 text-right font-semibold">LTP</th>
                    <th className="pb-2 text-right font-semibold">Current Value</th>
                    <th className="pb-2 text-right font-semibold">PnL</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((holding) => {
                    const livePrice = ticks.get(holding.symbol.toUpperCase())?.price ?? holding.ltp;
                    const unrealized = (livePrice - holding.avg_buy_price) * holding.quantity;
                    const currentVal = livePrice * holding.quantity;
                    return (
                      <tr key={holding.symbol} className="border-t border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.015)] transition-colors">
                        <td className="py-2.5 font-bold text-[var(--nq-text-primary)]">{holding.symbol}</td>
                        <td className="py-2.5 text-right">{holding.quantity.toLocaleString("en-IN")}</td>
                        <td className="py-2.5 text-right">{formatMoney(holding.avg_buy_price)}</td>
                        <td className="py-2.5 text-right font-bold text-[var(--nq-accent-cyan)]">{formatMoney(livePrice)}</td>
                        <td className="py-2.5 text-right">{formatMoney(currentVal)}</td>
                        <td className={`py-2.5 text-right font-bold ${unrealized >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
                          {formatMoney(unrealized)}
                        </td>
                      </tr>
                    );
                  })}
                  {!loading && holdings.length === 0 ? (
                    <tr>
                      <td className="py-4 text-[var(--nq-text-secondary)] text-center" colSpan={6}>
                        No holdings returned by portfolio contract.
                      </td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </article>

            {/* Risk Metrics side column */}
            <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4 flex flex-col justify-between">
              <div>
                <h2 className="mb-3 text-sm font-semibold text-[var(--nq-text-secondary)] uppercase tracking-wider text-[10px]">Risk Metrics</h2>
                <div className="space-y-2 text-xs font-mono">
                  {[
                    ["Sharpe Ratio", typeof risk?.sharpe === "number" ? risk.sharpe.toFixed(2) : "--"],
                    ["Sortino Ratio", typeof risk?.sortino === "number" ? risk.sortino.toFixed(2) : "--"],
                    ["Value at Risk (95%)", formatPct(risk?.var_95)],
                    ["CVaR Expected Shortfall", formatPct(risk?.cvar_95)],
                    ["Alpha (vs Benchmark)", typeof risk?.alpha === "number" ? risk.alpha.toFixed(2) : "--"],
                  ].map(([key, value]) => (
                    <div key={key} className="flex items-center justify-between rounded bg-[rgba(255,255,255,0.02)] px-3 py-1.5 border border-[rgba(255,255,255,0.02)]">
                      <span>{key}</span>
                      <span className="font-bold">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="mt-4 rounded bg-[rgba(0,212,245,0.03)] border border-[rgba(0,212,245,0.08)] p-3 text-[10px] text-[var(--nq-text-secondary)]">
                <strong>Standard Deviation Alert:</strong> Modern portfolio theory ratios indicate portfolio risk profile remains aligned with passive benchmark volatility indices.
              </div>
            </article>
          </div>
        )}

        {/* POSITIONS TAB */}
        {activeTab === "positions" && (
          <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4 overflow-x-auto">
            <table className="min-w-full text-xs font-mono">
              <thead>
                <tr className="text-[var(--nq-text-secondary)] border-b border-[var(--nq-border)] pb-2 text-[10px] uppercase">
                  <th className="pb-2 text-left font-semibold">Instrument</th>
                  <th className="pb-2 text-center font-semibold">Product</th>
                  <th className="pb-2 text-right font-semibold">Qty</th>
                  <th className="pb-2 text-right font-semibold">Avg Price</th>
                  <th className="pb-2 text-right font-semibold">LTP</th>
                  <th className="pb-2 text-right font-semibold">Realized P&L</th>
                  <th className="pb-2 text-right font-semibold">Unrealized P&L</th>
                  <th className="pb-2 text-right font-semibold">Total P&L</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos) => (
                  <tr key={pos.symbol} className="border-t border-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.015)] transition-colors">
                    <td className="py-2.5 font-bold text-[var(--nq-text-primary)]">{pos.symbol}</td>
                    <td className="py-2.5 text-center">
                      <span className="bg-[rgba(255,255,255,0.05)] border border-[rgba(255,255,255,0.08)] rounded px-1 text-[8px] font-bold text-[var(--nq-text-secondary)]">
                        {pos.product}
                      </span>
                    </td>
                    <td className={`py-2.5 text-right ${pos.qty > 0 ? "text-[var(--nq-accent-cyan)]" : "text-[var(--nq-text-muted)]"}`}>{pos.qty}</td>
                    <td className="py-2.5 text-right">{formatMoney(pos.avgPrice)}</td>
                    <td className="py-2.5 text-right font-bold text-[var(--nq-accent-cyan)]">{formatMoney(pos.ltp)}</td>
                    <td className={`py-2.5 text-right ${pos.realized >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
                      {pos.realized !== 0 ? formatMoney(pos.realized) : "0.00"}
                    </td>
                    <td className={`py-2.5 text-right font-semibold ${pos.unrealized >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
                      {pos.qty > 0 ? formatMoney(pos.unrealized) : "0.00"}
                    </td>
                    <td className={`py-2.5 text-right font-bold ${pos.totalPnl >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
                      {formatMoney(pos.totalPnl)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </article>
        )}

        {/* TRADE JOURNAL TAB */}
        {activeTab === "journal" && (
          <div className="grid gap-6 lg:grid-cols-[1fr_2fr]">
            {/* Submission Grid form */}
            <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4 h-fit">
              <h3 className="text-xs uppercase tracking-wider text-[var(--nq-text-secondary)] font-bold mb-3">Add Trade Review Note</h3>
              <form onSubmit={handleSubmitJournal} className="space-y-3 font-mono text-[10px]">
                <div className="grid grid-cols-2 gap-2">
                  <label className="block uppercase text-[8px] text-[var(--nq-text-secondary)] font-bold">
                    Ticker *
                    <input
                      type="text"
                      placeholder="e.g. AAPL"
                      value={jsym}
                      onChange={e => setJsym(e.target.value)}
                      className="mt-1 w-full rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-2 py-1 text-xs text-[var(--nq-text-primary)] outline-none"
                    />
                  </label>
                  <label className="block uppercase text-[8px] text-[var(--nq-text-secondary)] font-bold">
                    Direction
                    <select
                      value={jdir}
                      onChange={e => setJdir(e.target.value)}
                      className="mt-1 w-full rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-2 py-1 text-xs text-[var(--nq-text-primary)] outline-none"
                    >
                      <option value="LONG">LONG</option>
                      <option value="SHORT">SHORT</option>
                    </select>
                  </label>
                </div>

                <div className="grid grid-cols-3 gap-2">
                  <label className="block uppercase text-[8px] text-[var(--nq-text-secondary)] font-bold">
                    Entry Price
                    <input
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      value={jentryPrice}
                      onChange={e => setJentryPrice(e.target.value)}
                      className="mt-1 w-full rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-2 py-1 text-xs text-[var(--nq-text-primary)] outline-none"
                    />
                  </label>
                  <label className="block uppercase text-[8px] text-[var(--nq-text-secondary)] font-bold">
                    Exit Price
                    <input
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      value={jexitPrice}
                      onChange={e => setJexitPrice(e.target.value)}
                      className="mt-1 w-full rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-2 py-1 text-xs text-[var(--nq-text-primary)] outline-none"
                    />
                  </label>
                  <label className="block uppercase text-[8px] text-[var(--nq-text-secondary)] font-bold">
                    Quantity
                    <input
                      type="number"
                      step="0.01"
                      placeholder="0"
                      value={jqty}
                      onChange={e => setJqty(e.target.value)}
                      className="mt-1 w-full rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-2 py-1 text-xs text-[var(--nq-text-primary)] outline-none"
                    />
                  </label>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <label className="block uppercase text-[8px] text-[var(--nq-text-secondary)] font-bold">
                    Rating (1-5 Stars)
                    <select
                      value={jrating}
                      onChange={e => setJrating(Number(e.target.value))}
                      className="mt-1 w-full rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-2 py-1 text-xs text-[var(--nq-text-primary)] outline-none"
                    >
                      {[5, 4, 3, 2, 1].map(n => (
                        <option key={n} value={n}>{"★".repeat(n) + "☆".repeat(5-n)}</option>
                      ))}
                    </select>
                  </label>
                  <label className="block uppercase text-[8px] text-[var(--nq-text-secondary)] font-bold">
                    Strategy Tags
                    <input
                      type="text"
                      placeholder="e.g. breakout, fvg"
                      value={jtags}
                      onChange={e => setJtags(e.target.value)}
                      className="mt-1 w-full rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-2 py-1 text-xs text-[var(--nq-text-primary)] outline-none"
                    />
                  </label>
                </div>

                <label className="block uppercase text-[8px] text-[var(--nq-text-secondary)] font-bold">
                  Mental notes & Emotions *
                  <textarea
                    placeholder="Describe mental focus, setup validation, mistakes..."
                    rows={4}
                    value={jnotes}
                    onChange={e => setJnotes(e.target.value)}
                    className="mt-1 w-full rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-2.5 py-1.5 text-xs text-[var(--nq-text-primary)] outline-none resize-none font-sans"
                  />
                </label>

                {journalError && <p className="text-[10px] text-[#FF3B5C] font-bold">{journalError}</p>}
                <button
                  type="submit"
                  disabled={journalSubmitting}
                  className="w-full rounded bg-[var(--nq-accent-cyan)] hover:bg-[#00b4d8] text-black font-bold uppercase tracking-wider py-2 transition disabled:opacity-50"
                >
                  {journalSubmitting ? "Logging..." : "Add Journal Log"}
                </button>
              </form>
            </article>

            {/* List entries */}
            <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4 max-h-[500px] overflow-y-auto ds-scrollable">
              <h3 className="text-xs uppercase tracking-wider text-[var(--nq-text-secondary)] font-bold mb-3 border-b border-[var(--nq-border)] pb-2">
                Trade Logs Ledger
              </h3>
              <div className="space-y-3">
                {journals.map((entry) => (
                  <div key={entry.id} className="rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] p-3 relative hover:border-[rgba(255,255,255,0.12)] transition">
                    <button
                      onClick={() => handleDeleteJournal(entry.id)}
                      className="absolute right-3 top-3 text-[10px] text-[var(--nq-text-secondary)] hover:text-[var(--nq-accent-red)] transition-colors"
                      title="Delete entry"
                    >
                      Delete
                    </button>
                    <div className="flex gap-2 items-center flex-wrap">
                      <span className="font-bold text-xs text-[var(--nq-accent-cyan)] font-mono">{entry.symbol}</span>
                      <span className={`text-[8px] font-bold px-1 border rounded ${entry.direction === "SHORT" ? "border-[var(--nq-accent-red)] text-[var(--nq-accent-red)] bg-[rgba(255,59,92,0.08)]" : "border-[var(--nq-accent-green)] text-[var(--nq-accent-green)] bg-[rgba(0,230,118,0.08)]"}`}>
                        {entry.direction ?? "LONG"}
                      </span>
                      <span className="text-[10px] text-yellow-500">{"★".repeat(entry.rating ?? 5)}</span>
                      <span className="text-[8px] text-[var(--nq-text-secondary)] ml-auto font-mono">{new Date(entry.created_at).toLocaleString()}</span>
                    </div>

                    {entry.quantity || entry.entry_price || entry.exit_price ? (
                      <div className="mt-2 text-[9px] font-mono text-[var(--nq-text-secondary)] border-y border-[rgba(255,255,255,0.03)] py-1 flex gap-4">
                        {entry.quantity ? <span>Qty: {entry.quantity}</span> : null}
                        {entry.entry_price ? <span>Entry: ₹{entry.entry_price}</span> : null}
                        {entry.exit_price ? <span>Exit: ₹{entry.exit_price}</span> : null}
                        {entry.entry_price && entry.exit_price && entry.quantity ? (
                          <span className={`ml-auto font-bold ${((entry.exit_price - entry.entry_price) * (entry.direction === "SHORT" ? -1 : 1)) >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
                            PnL: ₹{((entry.exit_price - entry.entry_price) * entry.quantity * (entry.direction === "SHORT" ? -1 : 1)).toFixed(2)}
                          </span>
                        ) : null}
                      </div>
                    ) : null}

                    <p className="mt-2 text-xs text-[var(--nq-text-secondary)] leading-relaxed font-sans">{entry.notes}</p>
                    
                    {entry.tags ? (
                      <div className="mt-2 flex gap-1.5 flex-wrap">
                        {entry.tags.split(",").map(t => (
                          <span key={t} className="bg-[rgba(255,255,255,0.04)] text-[var(--nq-text-muted)] text-[8px] font-mono rounded px-1 py-0.5 border border-[rgba(255,255,255,0.04)]">
                            #{t.trim()}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ))}
                {journals.length === 0 && (
                  <div className="py-8 text-center text-xs text-[var(--nq-text-secondary)] opacity-60">
                    No trade logs entered yet. Submit your first audit log on the left.
                  </div>
                )}
              </div>
            </article>
          </div>
        )}
      </div>

      {/* Performance chart at bottom */}
      <section className="mt-6 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
        <h2 className="mb-3 text-sm font-semibold text-[var(--nq-text-secondary)] uppercase tracking-wider text-[10px]">Performance Equity Curve</h2>
        <div className="h-44 rounded bg-[rgba(255,255,255,0.02)] p-2 border border-[rgba(255,255,255,0.02)]">
          <div className="flex h-full items-end gap-[2px]">
            {(loading ? Array.from({ length: 90 }, () => 20) : performanceBars).map((height, index) => (
              <div key={`perf-${index}`} className="w-full rounded-sm bg-[var(--nq-accent-green)]/50 hover:bg-[var(--nq-accent-green)] transition-colors" style={{ height: `${height}%` }} />
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}