"use client";

import { useEffect, useMemo, useState } from "react";
import { Search, Plus, Trash2 } from "lucide-react";
import { safeFormat } from "@/lib/formatters";
import type { SignalResponse } from "@/types/intelligence";
import { usePriceFeed } from "@/hooks/usePriceFeed";

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

function getExchangeAndName(symbol: string): { exchange: string; name: string } {
  const sym = symbol.toUpperCase();
  if (sym.endsWith(".NS")) {
    const base = sym.split(".NS")[0] ?? sym;
    return { exchange: "NSE", name: `${base} Ltd.` };
  }
  if (sym.endsWith("-USD") || sym.includes("BTC") || sym.includes("ETH") || sym.includes("SOL") || sym.includes("BNB") || sym.includes("XRP")) {
    const base = sym.replace("-USD", "");
    return { exchange: "CRYPTO", name: `${base} Protocol` };
  }
  return { exchange: "NASDAQ", name: `${sym} Inc.` };
}

function getSharpeRatio(symbol: string): string {
  const sym = symbol.toUpperCase();
  const map: Record<string, string> = {
    "RELIANCE.NS": "1.34",
    "TCS.NS": "1.45",
    "INFY.NS": "1.12",
    "HDFCBANK.NS": "1.28",
    "ICICIBANK.NS": "1.52",
    "SBIN.NS": "1.21",
    "ITC.NS": "1.09",
    "LT.NS": "1.30",
    "AAPL": "1.42",
    "MSFT": "1.55",
    "GOOGL": "1.38",
    "AMZN": "1.24",
    "BTC-USD": "1.65",
    "ETH-USD": "1.51",
    "SOL-USD": "1.89",
  };
  return map[sym] || "1.25";
}

function getSector(symbol: string): string {
  const sym = symbol.toUpperCase();
  if (sym === "RELIANCE.NS") return "Energy & Conglomerate";
  if (["TCS.NS", "INFY.NS", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "NFLX"].includes(sym)) return "Technology";
  if (["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "JPM"].includes(sym)) return "Financials";
  if (sym === "ITC.NS") return "Consumer Goods";
  if (sym === "LT.NS") return "Industrials";
  if (sym === "SUNPHARMA.NS") return "Healthcare";
  if (sym.endsWith("-USD") || ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE"].some(c => sym.includes(c))) return "Cryptocurrencies";
  return "Others";
}

const Sparkline = ({ data }: { data: number[] }) => {
  if (!data || data.length < 2) return <div className="w-10 h-4 border-b border-dashed border-[var(--nq-border)] opacity-30" />;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const width = 40;
  const height = 16;
  const points = data
    .map((val, idx) => {
      const x = (idx / (data.length - 1)) * width;
      const y = height - ((val - min) / range) * height;
      return `${x},${y}`;
    })
    .join(" ");

  const isUp = data[data.length - 1]! >= data[0]!;
  return (
    <svg width={width} height={height} className="opacity-80">
      <polyline
        fill="none"
        stroke={isUp ? "var(--accent-green)" : "var(--accent-red)"}
        strokeWidth="1.5"
        points={points}
      />
    </svg>
  );
};

function getIsMarketClosed(): boolean {
  const options = { timeZone: "Asia/Kolkata" };
  let istString: string;
  try {
    istString = new Date().toLocaleString("en-US", options);
  } catch (e) {
    istString = new Date().toLocaleString();
  }
  const istDate = new Date(istString);
  const day = istDate.getDay(); // 0 = Sunday, 6 = Saturday
  const hours = istDate.getHours();
  const minutes = istDate.getMinutes();
  const totalMinutes = hours * 60 + minutes;

  const isOpenDay = day >= 1 && day <= 5; // Monday to Friday
  const isOpenTime = totalMinutes >= 555 && totalMinutes < 930; // 9:15 to 15:30
  return !(isOpenDay && isOpenTime);
}

export default function Watchlist({ signals, selectedSymbol, onSelectSymbol }: WatchlistProps): JSX.Element {
  const [isClosed, setIsClosed] = useState<boolean>(getIsMarketClosed());

  useEffect(() => {
    const timer = setInterval(() => {
      setIsClosed(getIsMarketClosed());
    }, 10000);
    return () => clearInterval(timer);
  }, []);

  const [activeTab, setActiveTab] = useState<number>(0);
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

  const visibleSignals = useMemo(() => {
    return activeSymbols
      .map((sym) => signals.find((s) => s.symbol.toUpperCase() === sym.toUpperCase()))
      .filter((item): item is SignalResponse => item !== undefined);
  }, [activeSymbols, signals]);

  const symbols = useMemo(() => visibleSignals.map((s) => s.symbol), [visibleSignals]);
  const { ticks } = usePriceFeed(symbols);

  const [tickHistories, setTickHistories] = useState<Record<string, number[]>>({});
  const [groupBySector, setGroupBySector] = useState<boolean>(false);
  const [collapsedSectors, setCollapsedSectors] = useState<Record<string, boolean>>({});
  const [draggedIdx, setDraggedIdx] = useState<number | null>(null);

  useEffect(() => {
    setTickHistories((prev) => {
      const copy = { ...prev };
      let changed = false;
      ticks.forEach((tick, sym) => {
        const hist = copy[sym] || [];
        if (hist.length === 0 || hist[hist.length - 1] !== tick.price) {
          const nextHist = [...hist, tick.price].slice(-10);
          copy[sym] = nextHist;
          changed = true;
        }
      });
      return changed ? copy : prev;
    });
  }, [ticks]);

  const handleDragStart = (idx: number) => {
    if (activeTab === 4) return;
    setDraggedIdx(idx);
  };

  const handleDragOver = (e: React.DragEvent, targetIdx: number) => {
    e.preventDefault();
    if (draggedIdx === null || draggedIdx === targetIdx || activeTab === 4) return;

    setWlLists((prev) => {
      const copy = [...prev];
      const currentList = [...(copy[activeTab] || [])];
      const item = currentList[draggedIdx];
      if (item) {
        currentList.splice(draggedIdx, 1);
        currentList.splice(targetIdx, 0, item);
        copy[activeTab] = currentList;
      }
      return copy;
    });
    setDraggedIdx(targetIdx);
  };

  const handleDragEnd = () => {
    setDraggedIdx(null);
  };

  const toggleSector = (sector: string) => {
    setCollapsedSectors((prev) => ({
      ...prev,
      [sector]: !prev[sector],
    }));
  };

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

  const groupedSignals = useMemo(() => {
    if (!groupBySector) return null;
    const groups: Record<string, SignalResponse[]> = {};
    visibleSignals.forEach((sig) => {
      const sec = getSector(sig.symbol);
      if (!groups[sec]) groups[sec] = [];
      groups[sec].push(sig);
    });
    return groups;
  }, [visibleSignals, groupBySector]);

  const renderRow = (item: SignalResponse, index: number) => {
    const selected = item.symbol === selectedSymbol;
    const regimeDotColor =
      item.regime.state === "BULL"
        ? "bg-[var(--accent-green)] shadow-[0_0_8px_rgba(0,230,118,0.5)]"
        : item.regime.state === "BEAR"
          ? "bg-[var(--accent-red)] shadow-[0_0_8px_rgba(255,59,92,0.5)]"
          : item.regime.state === "CRISIS"
            ? "bg-[var(--accent-red)] shadow-[0_0_8px_rgba(255,59,92,0.5)]"
            : "bg-[var(--accent-amber)] shadow-[0_0_8px_rgba(255,184,0,0.5)]";

    const { exchange, name } = getExchangeAndName(item.symbol);
    const sharpe = getSharpeRatio(item.symbol);
    const tick = ticks.get(item.symbol.toUpperCase());
    const ltpText = tick ? `₹${safeFormat(tick.price, 2)}` : "--";
    const changePct = tick ? tick.change_pct : null;
    const isUp = changePct !== null && changePct >= 0;
    const hist = tickHistories[item.symbol.toUpperCase()] || [];

    return (
      <div
        key={`${activeTab}-${item.symbol}`}
        onClick={() => onSelectSymbol(item.symbol)}
        draggable={activeTab !== 4 && !groupBySector}
        onDragStart={() => handleDragStart(index)}
        onDragOver={(e) => handleDragOver(e, index)}
        onDragEnd={handleDragEnd}
        className={`relative flex w-full cursor-pointer flex-col rounded border px-3 py-2 transition-all duration-200 group ${
          selected
            ? "border-[var(--nq-accent)] bg-[rgba(0,212,245,0.04)] shadow-[0_0_12px_rgba(0,212,245,0.05)]"
            : "border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] hover:border-[rgba(255,255,255,0.12)] hover:bg-[rgba(255,255,255,0.02)]"
        } ${draggedIdx === index ? "opacity-45 animate-pulse" : ""}`}
      >
        {/* Main row */}
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-0.5">
            <div className="flex items-center gap-1.5">
              <span className={`h-1.5 w-1.5 rounded-full ${regimeDotColor}`} />
              <span className="font-mono text-xs font-bold text-[var(--nq-text-primary)]">
                {item.symbol}
              </span>
              <span className="rounded bg-[rgba(255,255,255,0.05)] px-1 py-0.2 text-[7px] text-[var(--nq-text-secondary)] font-mono font-semibold uppercase tracking-wider">
                {exchange}
              </span>
            </div>
            <span className="block font-sans text-[9px] text-[var(--nq-text-secondary)] truncate max-w-[120px]" title={name}>
              {name}
            </span>
          </div>

          {/* Sparkline in the middle */}
          <div className="hidden xs:block mx-1">
            <Sparkline data={hist} />
          </div>
          
          <div className="flex items-center gap-4 text-right transition-all group-hover:opacity-0">
            <div className="flex flex-col items-end">
              <span className="rounded bg-[rgba(0,212,245,0.08)] px-1.5 py-0.5 text-[8px] font-mono font-semibold text-[var(--nq-accent-cyan)] border border-[rgba(0,212,245,0.15)]">
                SR {sharpe}
              </span>
              <span className={`mt-0.5 block text-[8px] font-bold uppercase tracking-wider ${directionColor(item.ensemble.direction)}`}>
                {item.ensemble.direction.replace("_", " ")}
              </span>
            </div>
            
            <div className="flex flex-col items-end min-w-[70px]">
              <span className="font-mono text-xs font-bold text-[var(--nq-text-primary)]">
                {ltpText}
              </span>
              {changePct !== null ? (
                <span className={`font-mono text-[9px] font-semibold ${isUp ? "text-[var(--accent-green)]" : "text-[var(--accent-red)]"}`}>
                  {isUp ? "+" : ""}{changePct.toFixed(2)}%
                </span>
              ) : (
                <span className="font-mono text-[9px] text-[var(--nq-text-muted)]">--</span>
              )}
            </div>
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
  };

  return (
    <aside className="flex h-full flex-col border-b border-[var(--nq-border)] bg-[var(--nq-bg-surface)] p-3 lg:border-b-0 lg:border-r ds-page-transition">
      {/* Watchlist Tabs Header (Zerodha style) */}
      <div className="mb-2 flex items-center justify-between border-b border-[var(--nq-border)] pb-2">
        <div className="flex gap-1 overflow-x-auto ds-scrollable pr-2">
          {[1, 2, 3, 4].map((num, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => {
                setActiveTab(idx);
                setGroupBySector(false);
              }}
              className={`rounded px-2.5 py-1 text-[10px] font-semibold font-mono transition-colors ${
                activeTab === idx && !groupBySector
                  ? "bg-[rgba(0,212,245,0.12)] text-[var(--nq-accent)] border border-[rgba(0,212,245,0.3)]"
                  : "text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)] border border-transparent"
              }`}
            >
              WL {num}
            </button>
          ))}
          <button
            type="button"
            onClick={() => {
              setActiveTab(4);
              setGroupBySector(false);
            }}
            className={`rounded px-2.5 py-1 text-[10px] font-semibold transition-colors ${
              activeTab === 4 && !groupBySector
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

      {isClosed && signals.length > 0 && (
        <div className="mb-2 rounded border border-[rgba(255,59,92,0.3)] bg-[rgba(255,59,92,0.06)] px-2.5 py-1.5 text-[10px] text-[#FF3B5C] font-mono flex items-center justify-between shrink-0">
          <span className="font-bold">Market Closed</span>
          {signals.find((s) => s.timestamp)?.timestamp && (
            <span className="opacity-85">
              Last Close: {new Date(signals.find((s) => s.timestamp)!.timestamp).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}
            </span>
          )}
        </div>
      )}

      {/* Sector grouping toggle */}
      <div className="mb-2 flex items-center justify-between border-b border-[var(--nq-border)] pb-2 pt-0.5">
        <span className="text-[10px] text-[var(--nq-text-secondary)] font-mono font-semibold uppercase tracking-wider">Group by Sector</span>
        <button
          type="button"
          onClick={() => setGroupBySector(!groupBySector)}
          className={`rounded px-2 py-0.5 text-[9px] font-bold font-mono transition-all border ${
            groupBySector
              ? "bg-[rgba(0,212,245,0.12)] border-[rgba(0,212,245,0.4)] text-[var(--nq-accent-cyan)] shadow-[0_0_8px_rgba(0,212,245,0.08)]"
              : "border-[var(--nq-border)] text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)]"
          }`}
        >
          {groupBySector ? "ON" : "OFF"}
        </button>
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
        {groupBySector && groupedSignals ? (
          Object.entries(groupedSignals).map(([sector, sectorSignals]) => {
            const isCollapsed = collapsedSectors[sector] ?? false;
            return (
              <div key={sector} className="space-y-1">
                <button
                  type="button"
                  onClick={() => toggleSector(sector)}
                  className="flex w-full items-center justify-between rounded bg-[rgba(255,255,255,0.02)] px-2.5 py-1 text-[9px] font-bold font-mono text-[var(--nq-text-secondary)] border border-[var(--nq-border)] hover:bg-white/5 transition-colors"
                >
                  <span className="uppercase tracking-wider">{sector} ({sectorSignals.length})</span>
                  <span>{isCollapsed ? "+" : "-"}</span>
                </button>
                {!isCollapsed && (
                  <div className="space-y-1.5 pl-1">
                    {sectorSignals.map((item) => {
                      const idx = visibleSignals.findIndex((s) => s.symbol === item.symbol);
                      return renderRow(item, idx);
                    })}
                  </div>
                )}
              </div>
            );
          })
        ) : (
          visibleSignals.map((item, index) => renderRow(item, index))
        )}

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
