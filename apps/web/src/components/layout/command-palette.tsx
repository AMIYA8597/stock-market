"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  TrendingUp,
  Bitcoin,
  BarChart3,
  ArrowRight,
} from "lucide-react";
import { cn } from "@neuroquant/ui";
import { useUIStore } from "@/stores/ui-store";

interface SearchItem {
  symbol: string;
  name: string;
  type: "stock" | "crypto" | "etf" | "index";
  exchange?: string;
}

const POPULAR_SEARCHES: SearchItem[] = [
  { symbol: "RELIANCE.NS", name: "Reliance Industries", type: "stock", exchange: "NSE" },
  { symbol: "TCS.NS", name: "Tata Consultancy Services", type: "stock", exchange: "NSE" },
  { symbol: "INFY.NS", name: "Infosys", type: "stock", exchange: "NSE" },
  { symbol: "HDFCBANK.NS", name: "HDFC Bank", type: "stock", exchange: "NSE" },
  { symbol: "AAPL", name: "Apple Inc.", type: "stock", exchange: "NASDAQ" },
  { symbol: "MSFT", name: "Microsoft Corporation", type: "stock", exchange: "NASDAQ" },
  { symbol: "GOOGL", name: "Alphabet Inc.", type: "stock", exchange: "NASDAQ" },
  { symbol: "BTC-USD", name: "Bitcoin", type: "crypto" },
  { symbol: "ETH-USD", name: "Ethereum", type: "crypto" },
];

const typeIcons: Record<string, typeof TrendingUp> = {
  stock: TrendingUp,
  crypto: Bitcoin,
  etf: BarChart3,
  index: BarChart3,
};

export function CommandPalette() {
  const router = useRouter();
  const { commandPaletteOpen, closeCommandPalette } = useUIStore();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);

  const filteredItems = query.length === 0
    ? POPULAR_SEARCHES
    : POPULAR_SEARCHES.filter(
        (item) =>
          item.symbol.toLowerCase().includes(query.toLowerCase()) ||
          item.name.toLowerCase().includes(query.toLowerCase())
      );

  const handleSelect = useCallback(
    (item: SearchItem) => {
      router.push(`/market/${encodeURIComponent(item.symbol)}`);
      closeCommandPalette();
      setQuery("");
    },
    [router, closeCommandPalette]
  );

  // Keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        useUIStore.getState().commandPaletteOpen
          ? closeCommandPalette()
          : useUIStore.getState().openCommandPalette();
      }

      if (!commandPaletteOpen) return;

      if (e.key === "Escape") {
        closeCommandPalette();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, filteredItems.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        const item = filteredItems[selectedIndex];
        if (item) handleSelect(item);
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [commandPaletteOpen, closeCommandPalette, filteredItems, selectedIndex, handleSelect]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  if (!commandPaletteOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={closeCommandPalette}
      />

      {/* Modal */}
      <div className="relative w-full max-w-lg animate-slide-down rounded-nq-xl border border-nq-border bg-nq-bg-secondary shadow-nq-elevated overflow-hidden">
        {/* Input */}
        <div className="flex items-center gap-3 border-b border-nq-border px-4 py-3">
          <Search className="h-5 w-5 text-nq-text-tertiary flex-shrink-0" />
          <input
            type="text"
            placeholder="Search stocks, crypto, pages..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
            className="flex-1 bg-transparent text-sm text-nq-text-primary placeholder:text-nq-text-tertiary outline-none"
          />
          <kbd className="rounded border border-nq-border bg-nq-bg-elevated px-1.5 py-0.5 text-[10px] font-mono text-nq-text-tertiary">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto py-2">
          {query.length === 0 && (
            <div className="px-4 py-1.5 text-[10px] font-medium text-nq-text-tertiary uppercase tracking-wider">
              Popular
            </div>
          )}
          {filteredItems.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-nq-text-tertiary">
              No results found for &ldquo;{query}&rdquo;
            </div>
          ) : (
            filteredItems.map((item, idx) => {
              const Icon = typeIcons[item.type] ?? TrendingUp;
              return (
                <button
                  key={item.symbol}
                  onClick={() => handleSelect(item)}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={cn(
                    "flex w-full items-center gap-3 px-4 py-2.5 text-left transition-colors",
                    idx === selectedIndex
                      ? "bg-nq-bg-card text-nq-text-primary"
                      : "text-nq-text-secondary hover:bg-nq-bg-card"
                  )}
                >
                  <Icon className="h-4 w-4 flex-shrink-0 text-nq-text-tertiary" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm font-semibold">
                        {item.symbol}
                      </span>
                      {item.exchange && (
                        <span className="text-[10px] text-nq-text-tertiary">
                          {item.exchange}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-nq-text-tertiary truncate">
                      {item.name}
                    </div>
                  </div>
                  {idx === selectedIndex && (
                    <ArrowRight className="h-3.5 w-3.5 text-nq-accent flex-shrink-0" />
                  )}
                </button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
