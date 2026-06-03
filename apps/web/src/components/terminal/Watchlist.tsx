"use client";

import { useMemo, useState } from "react";
import { Search, Plus, Trash2 } from "lucide-react";
import { safeFormat } from "@/lib/formatters";
import type { SignalResponse } from "@/types/intelligence";

interface WatchlistProps {
  signals: SignalResponse[];
  selectedSymbol: string;
  onSelectSymbol: (symbol: string) => void;
}

const ALL_SEARCHABLE_TICKERS = [
  // NSE
  "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
  "SBIN.NS", "ITC.NS", "LT.NS", "AXISBANK.NS", "SUNPHARMA.NS",
  // US
  "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "NFLX", "AMD", "JPM",
  // CRYPTO
  "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", "DOGE-USD"
];

const directionColor = (direction: string): string => {
  if (direction.includes("BUY")) return "text-[var(--accent-green)]";
  if (direction.includes("SELL")) return "text-[var(--accent-red)]";
  return "text-[var(--accent-amber)]";
};

export default function Watchlist({ signals, selectedSymbol, onSelectSymbol }: WatchlistProps): JSX.Element {
  const [activeTab, setActiveTab] = useState<number>(0); // 0 to 3 for custom watchlists, 4 for Market
  const [searchQuery, setSearchQuery] = useState<string>("");

  // 4 custom lists + Market default
  const [wlLists, setWlLists] = useState<string[][]>([
    ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"],
    ["ICICIBANK.NS", "SBIN.NS", "ITC.NS", "LT.NS"],
    ["AAPL", "MSFT", "GOOGL", "AMZN"],
    ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD"]
  ]);

  const activeSymbols = useMemo(() => {
    if (activeTab === 4) {
      // Market tab - show all signals sorted by confidence
      return signals.map((s) => s.symbol);
    }
    return wlLists[activeTab] || [];
  }, [signals, activeTab, wlLists]);

  const makeMockSignal = (symbol: string): SignalResponse => {
    const isCrypto = symbol.includes("-USD");
    const isUS = !isCrypto && !symbol.includes(".NS");
    const basePrice = isCrypto ? 2500.0 : isUS ? 180.0 : 1500.0;
    return {
      symbol: symbol.toUpperCase(),
      timestamp: new Date().toISOString(),
      ensemble: {
        direction: "BUY",
        confidence: 0.62,
        kelly_fraction: 0.12,
        signal: "BUY"
      },
      regime: {
        state: "BULL",
        probs: { bull: 0.6, bear: 0.1, sideways: 0.2, crisis: 0.1 },
        transition_probs: { bull: 0.8, bear: 0.1, sideways: 0.1, crisis: 0.0 }
      },
      models: {
        tft: { p10: basePrice * 0.98, p50: basePrice, p90: basePrice * 1.02, raw_signal: 0.3, horizon_days: 5 },
        hmm_garch: { regime_signal: "BULL", vol_forecast_1d: 0.015, vol_forecast_21d: 0.07 },
        gnn: { spillover_risk: 0.05, embedding_norm: 1.0, top_correlated_assets: [] },
        lstm_attn: { raw_signal: 0.4, attention_peaks: [] },
        xgboost: { raw_signal: 0.35, top_features: [] }
      },
      model_weights: {}
    };
  };

  const visibleSignals = useMemo(() => {
    return activeSymbols.map((sym) => {
      const found = signals.find((s) => s.symbol.toUpperCase() === sym.toUpperCase());
      return found || makeMockSignal(sym);
    });
  }, [activeSymbols, signals]);

  const searchResults = useMemo(() => {
    if (!searchQuery.trim()) return [];
    const query = searchQuery.trim().toUpperCase();
    
    // Filter predefined search symbols
    const filtered = ALL_SEARCHABLE_TICKERS.filter(
      (t) => t.toUpperCase().includes(query) && !activeSymbols.includes(t)
    );

    // If search query is not empty and not in the list, allow adding it as a custom stock
    if (query && !ALL_SEARCHABLE_TICKERS.includes(query) && !activeSymbols.includes(query)) {
      filtered.push(query);
    }
    return filtered.slice(0, 5);
  }, [searchQuery, activeSymbols]);

  const handleAddSymbol = (symbol: string) => {
    if (activeTab === 4) return; // Cannot add to default Market tab
    setWlLists((prev) => {
      const copy = [...prev];
      const currentList = copy[activeTab] || [];
      if (!currentList.includes(symbol)) {
        copy[activeTab] = [...currentList, symbol];
      }
      return copy;
    });
    setSearchQuery("");
  };

  const handleRemoveSymbol = (symbol: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (activeTab === 4) return;
    setWlLists((prev) => {
      const copy = [...prev];
      const currentList = copy[activeTab] || [];
      copy[activeTab] = currentList.filter((s) => s !== symbol);
      return copy;
    });
  };

  const handleBuyShortcut = (symbol: string, e: React.MouseEvent) => {
    e.stopPropagation();
    onSelectSymbol(symbol);
    // Dispatch custom event to focus and set side to BUY in order ticket
    window.dispatchEvent(
      new CustomEvent("select-order-side", { detail: { side: "BUY", symbol } })
    );
  };

  const handleSellShortcut = (symbol: string, e: React.MouseEvent) => {
    e.stopPropagation();
    onSelectSymbol(symbol);
    // Dispatch custom event to focus and set side to SELL in order ticket
    window.dispatchEvent(
      new CustomEvent("select-order-side", { detail: { side: "SELL", symbol } })
    );
  };

  return (
    <aside className="flex h-full flex-col border-b border-[var(--nq-border)] bg-[var(--nq-bg-surface)] p-3 lg:border-b-0 lg:border-r ds-page-transition">
      {/* Watchlist Tabs Header (Zerodha style) */}
      <div className="mb-3 flex items-center justify-between border-b border-[var(--nq-border)] pb-2">
        <div className="flex gap-1 overflow-x-auto ds-scrollable pr-2">
          {[1, 2, 3, 4].map((num, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setActiveTab(idx)}
              className={`rounded px-2.5 py-1 text-[10px] font-semibold font-mono transition-colors ${
                activeTab === idx
                  ? "bg-[rgba(0,212,245,0.12)] text-[var(--nq-accent)] border border-[rgba(0,212,245,0.3)]"
                  : "text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)] border border-transparent"
              }`}
            >
              WL {num}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setActiveTab(4)}
            className={`rounded px-2.5 py-1 text-[10px] font-semibold transition-colors ${
              activeTab === 4
                ? "bg-[rgba(0,212,245,0.12)] text-[var(--nq-accent)] border border-[rgba(0,212,245,0.3)]"
                : "text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)] border border-transparent"
            }`}
          >
            Market
          </button>
        </div>
        <span className="text-[10px] font-mono text-[var(--nq-text-secondary)] select-none">
          {activeSymbols.length} / 50
        </span>
      </div>

      {/* Search Input Bar */}
      {activeTab !== 4 && (
        <div className="relative mb-3">
          <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-2.5">
            <Search className="h-3.5 w-3.5 text-[var(--nq-text-secondary)]" />
          </div>
          <input
            type="text"
            placeholder="Search & add symbol... (e.g. AAPL, RELIANCE)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] py-1.5 pl-8 pr-3 text-xs text-[var(--nq-text-primary)] placeholder-[var(--nq-text-muted)] outline-none transition focus:border-[var(--nq-accent)] focus:bg-[rgba(255,255,255,0.04)]"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute inset-y-0 right-0 flex items-center pr-2.5 text-xs text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)]"
            >
              ×
            </button>
          )}

          {/* Search Dropdown Results */}
          {searchResults.length > 0 && (
            <div className="absolute left-0 right-0 top-full z-[100] mt-1 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-surface)] p-1 shadow-2xl nq-glass">
              {searchResults.map((ticker) => (
                <button
                  key={ticker}
                  type="button"
                  onClick={() => handleAddSymbol(ticker)}
                  className="flex w-full items-center justify-between rounded px-2.5 py-2 text-left text-xs text-[var(--nq-text-primary)] hover:bg-[rgba(255,255,255,0.05)] transition-colors group"
                >
                  <span className="font-mono">{ticker}</span>
                  <span className="flex items-center gap-1 text-[10px] text-[var(--nq-accent)] font-medium opacity-70 group-hover:opacity-100 transition-opacity">
                    <Plus className="h-3 w-3" /> Add to WL
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Watchlist Body Container */}
      <div className="flex-1 overflow-y-auto pr-1 space-y-1.5 ds-scrollable select-none">
        {visibleSignals.map((item) => {
          const selected = item.symbol === selectedSymbol;
          const regimeDotColor =
            item.regime.state === "BULL"
              ? "bg-[var(--accent-green)] shadow-[0_0_8px_rgba(0,230,118,0.5)]"
              : item.regime.state === "BEAR"
                ? "bg-[var(--accent-red)] shadow-[0_0_8px_rgba(255,59,92,0.5)]"
                : item.regime.state === "CRISIS"
                  ? "bg-[var(--accent-red)] shadow-[0_0_8px_rgba(255,59,92,0.5)]"
                  : "bg-[var(--accent-amber)] shadow-[0_0_8px_rgba(255,184,0,0.5)]";

          return (
            <div
              key={`${activeTab}-${item.symbol}`}
              onClick={() => onSelectSymbol(item.symbol)}
              className={`relative flex w-full cursor-pointer flex-col rounded border px-3 py-2 transition-all duration-200 group ${
                selected
                  ? "border-[var(--nq-accent)] bg-[rgba(0,212,245,0.04)]"
                  : "border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] hover:border-[rgba(255,255,255,0.12)] hover:bg-[rgba(255,255,255,0.02)]"
              }`}
            >
              {/* Main row */}
              <div className="flex items-center justify-between">
                <div>
                  <span className="flex items-center gap-1.5 font-mono text-xs font-semibold text-[var(--nq-text-primary)]">
                    <span className={`h-2.5 w-2.5 rounded-full ${regimeDotColor}`} />
                    {item.symbol}
                  </span>
                  <span className="mt-0.5 block font-mono text-[9px] text-[var(--nq-text-secondary)] uppercase">
                    {item.regime.state} Regime
                  </span>
                </div>
                <div className="text-right transition-all group-hover:opacity-0">
                  <span className={`block text-xs font-semibold ${directionColor(item.ensemble.direction)}`}>
                    {item.ensemble.direction}
                  </span>
                  <span className="block font-mono text-[9px] text-[var(--nq-text-secondary)]">
                    Conf: {safeFormat(Number(item.ensemble.confidence) * 100, 1)}%
                  </span>
                </div>
              </div>

              {/* Zerodha-Style hover shortcut overlays */}
              <div className="absolute inset-y-0 right-3 hidden items-center gap-1.5 opacity-0 group-hover:flex group-hover:opacity-100 transition-all duration-150">
                <button
                  type="button"
                  onClick={(e) => handleBuyShortcut(item.symbol, e)}
                  className="rounded bg-[rgba(0,230,118,0.15)] border border-[rgba(0,230,118,0.4)] px-2 py-1 text-[9px] font-bold text-[var(--accent-green)] hover:bg-[rgba(0,230,118,0.25)] transition-colors shadow-sm uppercase tracking-wider"
                >
                  Buy
                </button>
                <button
                  type="button"
                  onClick={(e) => handleSellShortcut(item.symbol, e)}
                  className="rounded bg-[rgba(255,59,92,0.15)] border border-[rgba(255,59,92,0.4)] px-2 py-1 text-[9px] font-bold text-[var(--accent-red)] hover:bg-[rgba(255,59,92,0.25)] transition-colors shadow-sm uppercase tracking-wider"
                >
                  Sell
                </button>
                {activeTab !== 4 && (
                  <button
                    type="button"
                    onClick={(e) => handleRemoveSymbol(item.symbol, e)}
                    className="rounded border border-[var(--nq-border)] p-1 text-[var(--nq-text-secondary)] hover:border-[var(--nq-accent-red)] hover:text-[var(--accent-red)] transition-colors bg-[rgba(255,255,255,0.02)]"
                    title="Remove from Watchlist"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                )}
              </div>
            </div>
          );
        })}

        {visibleSignals.length === 0 && (
          <div className="flex flex-col items-center justify-center py-10 text-center border border-dashed border-[var(--nq-border)] rounded-lg px-4 bg-[rgba(255,255,255,0.005)]">
            <p className="text-xs text-[var(--nq-text-secondary)] font-medium">Watchlist is empty</p>
            <p className="text-[10px] text-[var(--nq-text-secondary)] mt-1 opacity-70">Search and add symbols to start tracking</p>
          </div>
        )}
      </div>
    </aside>
  );
}
