"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchApi } from "@/lib/api-client";
import { Search, Plus, Trash2 } from "lucide-react";
import { safeFormat } from "@/lib/formatters";
import type { SignalResponse } from "@/types/intelligence";
import { usePriceFeed } from "@/hooks/usePriceFeed";

interface WatchlistProps {
  signals: SignalResponse[];
  wlLists?: string[][];
  selectedSymbol: string;
  onSelectSymbol: (symbol: string) => void;
  onAddSymbol?: (symbol: string, listId?: number) => void;
  onRemoveSymbol?: (symbol: string, listId?: number) => void;
}



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

function getSector(symbol: string): string {
  const sym = symbol.toUpperCase().replace(".NS", "");
  const sectors: Record<string, string[]> = {
    "Energy & Conglomerate": ["RELIANCE", "ADANIENT", "ADANIPORTS", "ADANIGREEN", "ADANIPOWER"],
    "Technology": ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "LTIM", "PERSISTENT", "OFSS", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "NFLX"],
    "Financials": ["HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK", "BAJFINANCE", "BAJAJFINSV", "INDUSINDBK", "BANKBARODA", "CANBK", "PNB", "IDFCFIRSTB", "SBILIFE", "HDFCLIFE", "ICICIPRULI", "CHOLAFIN", "LICI", "JPM"],
    "Consumer Goods": ["ITC", "HINDUNILVR", "NESTLEIND", "BRITANNIA", "TATACONSUM", "DABUR", "GODREJCP", "MARICO", "COLPAL"],
    "Industrials": ["LT", "SIEMENS", "HAL", "BOSCHLTD", "HAVELLS", "POLYCAB", "INDUSTOWER", "IRCTC"],
    "Healthcare": ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "AUROPHARMA", "LUPIN", "TORNTPHARM", "APOLLOHOSP", "MAXHEALTH"],
    "Automotive": ["MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "HEROMOTOCO", "EICHERMOT"],
    "Metals & Mining": ["TATASTEEL", "JSWSTEEL", "HINDALCO", "COALINDIA", "VEDL", "SAIL", "JINDALSTEL"],
    "Oil & Gas": ["ONGC", "BPCL", "IOC", "GAIL"],
    "Power & Utilities": ["NTPC", "POWERGRID", "TATAPOWER", "NHPC", "JSWENERGY", "RECLTD"],
    "Real Estate": ["DLF", "OBEROIRLTY", "LODHA"],
    "Building Materials": ["ULTRACEMCO", "GRASIM", "SHREECEM", "AMBUJACEM", "PIDILITIND", "ASIANPAINT", "BERGEPAINT"],
    "Retail & Consumer": ["TITAN", "TRENT", "NYKAA", "ZOMATO", "PAYTM", "PAGEIND"],
    "Chemicals": ["SRF", "UPL"],
    "Telecom": ["BHARTIARTL", "IDEA"],
  };
  for (const [sector, symbols] of Object.entries(sectors)) {
    if (symbols.includes(sym)) return sector;
  }
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

export default function Watchlist({ signals, wlLists = [], selectedSymbol, onSelectSymbol, onAddSymbol, onRemoveSymbol }: WatchlistProps): JSX.Element {
  const [isClosed, setIsClosed] = useState<boolean>(getIsMarketClosed());

  useEffect(() => {
    const timer = setInterval(() => {
      setIsClosed(getIsMarketClosed());
    }, 10000);
    return () => clearInterval(timer);
  }, []);

  const [activeTab, setActiveTab] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState<string>("");

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "/" || (e.key === "k" && (e.metaKey || e.ctrlKey))) {
        e.preventDefault();
        document.getElementById("watchlist-search-input")?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

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
  
  const lastCloseTimestamp = useMemo(() => {
    if (selectedSymbol) {
      const selSig = signals.find((s) => s.symbol.toUpperCase() === selectedSymbol.toUpperCase());
      if (selSig?.timestamp) return selSig.timestamp;
    }
    return signals.find((s) => s.timestamp)?.timestamp;
  }, [signals, selectedSymbol]);

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
    // Drag/drop ordering is currently disabled since it requires an API update to persist ordering.
    // To implement, we would call an API like `watchlistApi.reorder(activeTab, draggedIdx, targetIdx)`
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

  const [searchResults, setSearchResults] = useState<{ ticker: string; name: string }[]>([]);

  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    const query = searchQuery.trim();
    
    const fetchSearch = async () => {
      try {
        // Fallback to relative URL if no env var
        const data = await fetchApi<{ results: { ticker: string; name: string }[] }>(
          `/market/search?q=${encodeURIComponent(query)}`
        );
          const filtered = data.results.filter((r) => !activeSymbols.includes(r.ticker));
          setSearchResults(filtered.slice(0, 8));
        
      } catch (err) {
        console.error("Search failed", err);
      }
    };
    
    const timeoutId = setTimeout(fetchSearch, 300);
    return () => clearTimeout(timeoutId);
  }, [searchQuery, activeSymbols]);

  const handleAddSymbol = (symbol: string) => {
    if (activeTab === 4) return; // Cannot add to default Market tab
    
    // Call the parent handler
    if (onAddSymbol) {
      onAddSymbol(symbol, activeTab);
    }
    
    setSearchQuery("");
  };

  const handleRemoveSymbol = (e: React.MouseEvent, symbol: string) => {
    e.stopPropagation();
    if (activeTab === 4) return;
    
    // Call the parent handler
    if (onRemoveSymbol) {
      onRemoveSymbol(symbol, activeTab);
    }
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
    const tick = ticks.get(item.symbol.toUpperCase());
    const ltpText = tick ? `₹${safeFormat(tick.price, 2)}` : "--";
    const changePct = tick ? tick.change_pct : null;
    const isUp = changePct !== null && changePct >= 0;
    const hist = tickHistories[item.symbol.toUpperCase()] || [];

    return (
      <div
        key={`${activeTab}-${item.symbol}-${index}`}
        onClick={() => onSelectSymbol(item.symbol)}
        draggable={activeTab !== 4 && !groupBySector}
        onDragStart={() => handleDragStart(index)}
        onDragOver={(e) => handleDragOver(e, index)}
        onDragEnd={handleDragEnd}
        className={`relative flex w-full cursor-pointer flex-col rounded border-b border-l border-r border-t-0 px-2 py-1 transition-all duration-200 group ${
          selected
            ? "border-l-2 border-l-[var(--nq-accent)] bg-[rgba(0,212,245,0.04)] shadow-inner"
            : "border-[var(--nq-border)] bg-[rgba(255,255,255,0.01)] hover:border-l hover:border-l-[rgba(255,255,255,0.3)] hover:bg-[rgba(255,255,255,0.03)]"
        } ${draggedIdx === index ? "opacity-45 animate-pulse" : ""}`}
      >
        {/* Main row */}
        <div className="flex items-center justify-between gap-1 min-w-0">
          <div className="flex min-w-0 flex-1 flex-col gap-0.5">
            <div className="flex min-w-0 items-center gap-1">
              <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${regimeDotColor}`} />
              <span
                className="min-w-0 flex-1 truncate font-mono text-xs font-bold text-[var(--nq-text-primary)]"
                title={item.symbol}
              >
                {item.symbol}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <span className="rounded bg-[rgba(255,255,255,0.05)] px-1 py-0.2 text-[7px] text-[var(--nq-text-secondary)] font-mono font-semibold uppercase tracking-wider shrink-0">
                {exchange}
              </span>
              {tick?.source && (
                <span
                  className={`rounded border px-1 py-0.2 text-[7px] font-mono font-semibold uppercase tracking-wider shrink-0 ${
                    tick.source === "realtime"
                      ? "bg-[rgba(0,230,118,0.1)] text-[#00E676] border-[#00E676]"
                      : tick.source === "computed"
                      ? "bg-[rgba(179,136,255,0.1)] text-[#B388FF] border-[#B388FF]"
                      : "bg-[rgba(255,184,0,0.1)] text-[#FFB800] border-[#FFB800]"
                  }`}
                  title={tick.source === "realtime" ? "Real-time" : tick.source === "computed" ? "Computed" : "Delayed"}
                >
                  {tick.source === "realtime" ? "REAL-TIME" : tick.source === "computed" ? "COMPUTED" : "DELAYED"}
                </span>
              )}
            </div>
            <span className="block truncate font-sans text-[9px] text-[var(--nq-text-secondary)]" title={name}>
              {name}
            </span>
          </div>

          {/* Sparkline in the middle */}
          <div className="hidden xs:block mx-1">
            <Sparkline data={hist} />
          </div>
          
          <div className="flex shrink-0 items-center gap-2 text-right transition-all group-hover:opacity-0">
            <div className="flex flex-col items-end min-w-[38px]">
              <span className={`block text-[8px] font-bold uppercase tracking-wider ${directionColor(item.ensemble.direction)}`}>
                {item.ensemble.direction.replace("_", " ")}
              </span>
              <span className="mt-0.5 block text-[8px] font-mono text-[var(--nq-text-secondary)]">
                {Math.round(item.ensemble.confidence * 100)}%
              </span>
            </div>

            <div className="flex flex-col items-end min-w-[44px]">
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
              onClick={(e) => handleRemoveSymbol(e, item.symbol)}
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
              className={`rounded px-2.5 py-1 text-[10px] font-semibold font-mono transition-colors shrink-0 ${
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
            className={`rounded px-2.5 py-1 text-[10px] font-semibold transition-colors shrink-0 ${
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
          {lastCloseTimestamp && (
            <span className="opacity-85">
              Last Close: {new Date(lastCloseTimestamp).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}
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
            id="watchlist-search-input"
            type="text"
            placeholder="Search symbol... (Press '/' to focus)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] py-1 pl-8 pr-3 text-xs text-[var(--nq-text-primary)] placeholder-[var(--nq-text-muted)] outline-none transition focus:border-[var(--nq-accent)] focus:bg-[rgba(255,255,255,0.04)]"
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
                  key={ticker.ticker}
                  type="button"
                  onClick={() => handleAddSymbol(ticker.ticker)}
                  className="flex w-full items-center justify-between rounded px-2.5 py-2 text-left text-xs text-[var(--nq-text-primary)] hover:bg-[rgba(255,255,255,0.05)] transition-colors group"
                >
                  <span className="font-mono">{ticker.ticker} <span className="text-[10px] text-[var(--nq-text-secondary)] ml-1">{ticker.name}</span></span>
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
      <div className="flex items-center justify-between px-2 py-1 border-b border-[rgba(255,255,255,0.05)] font-mono text-[9px] font-semibold uppercase tracking-wider text-[var(--nq-text-secondary)] shrink-0 mt-1 sticky top-0 bg-[var(--nq-bg-surface)] z-10">
        <span>Symbol</span>
        <div className="flex items-center gap-2 text-right">
          <span className="min-w-[38px]">Signal</span>
          <span className="min-w-[44px]">LTP</span>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto pr-1 pt-1 space-y-0.5 ds-scrollable select-none relative">
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
