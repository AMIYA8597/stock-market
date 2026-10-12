/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
"use client";

import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import { contractsApi } from "@/lib/contracts-api";
import { intelligenceApi } from "@/lib/intelligence-api";
import { watchlistApi } from "@/lib/api-client";
import { useSignalFeed } from "@/hooks/useSignalFeed";
import type { SignalResponse } from "@/types/intelligence";

const DEFAULT_NIFTY50_SYMBOLS = [
  "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
  "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
  "AXISBANK", "LT", "WIPRO", "HCLTECH", "ASIANPAINT",
  "MARUTI", "SUNPHARMA", "TITAN", "ULTRACEMCO", "BAJFINANCE",
  "NESTLEIND", "M&M", "TATASTEEL", "NTPC", "POWERGRID",
  "ONGC", "COALINDIA", "JSWSTEEL", "GRASIM", "ADANIENT",
  "ADANIPORTS", "BAJAJFINSV", "TECHM", "DRREDDY", "CIPLA",
  "DIVISLAB", "BRITANNIA", "APOLLOHOSP", "TATACONSUM", "HEROMOTOCO",
  "EICHERMOT", "BPCL", "SHREECEM", "INDUSINDBK", "HINDALCO",
  "SBILIFE", "HDFCLIFE", "TATAMOTORS", "BAJAJ-AUTO", "TRENT",
];

interface TerminalDataState {
  symbols: string[];
  wlLists: string[][];
  selectedSymbol: string;
  selectedSignal: SignalResponse | null;
  watchlistSignals: SignalResponse[];
  loading: boolean;
  refreshing: boolean;
  signalStreamStatus: "connected" | "reconnecting" | "disconnected";
  error: string | null;
  setSelectedSymbol: (symbol: string) => void;
  refresh: () => Promise<void>;
  addWatchlistSymbol: (symbol: string, listId?: number) => Promise<void>;
  removeWatchlistSymbol: (symbol: string, listId?: number) => Promise<void>;
}

export const useTerminalData = (): TerminalDataState => {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [wlLists, setWlLists] = useState<string[][]>([[], [], [], []]);
  const [selectedSymbol, setSelectedSymbol] = useState<string>("");
  const [selectedSignal, setSelectedSignal] = useState<SignalResponse | null>(null);
  const [watchlistSignals, setWatchlistSignals] = useState<SignalResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const initializedRef = useRef<boolean>(false);
  const symbolsRef = useRef<string[]>([]);
  const { signals: liveSignals, status: signalStreamStatus } = useSignalFeed(symbols);

  const loadSymbols = useCallback(async (): Promise<string[]> => {
    try {
      const [l0, l1, l2, l3] = await Promise.all([
        watchlistApi.getWatchlist(0),
        watchlistApi.getWatchlist(1),
        watchlistApi.getWatchlist(2),
        watchlistApi.getWatchlist(3),
      ]);
      const newLists = [l0.symbols || [], l1.symbols || [], l2.symbols || [], l3.symbols || []];
      setWlLists(newLists);

      const combined = Array.from(new Set(newLists.flat()));
      if (combined.length > 0) {
        symbolsRef.current = combined;
        setSymbols(combined);
        return combined;
      }
    } catch (err) {
      console.warn("Failed to load user watchlist, falling back to defaults", err);
    }

    symbolsRef.current = DEFAULT_NIFTY50_SYMBOLS;
    setSymbols(DEFAULT_NIFTY50_SYMBOLS);
    setWlLists([DEFAULT_NIFTY50_SYMBOLS, [], [], []]);
    return DEFAULT_NIFTY50_SYMBOLS;
  }, []);

  const refreshAll = useCallback(
    async (background = false, sourceSymbols?: string[]): Promise<void> => {
      if (background && initializedRef.current) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);
      const rawSymbolsToLoad = sourceSymbols ?? (symbolsRef.current.length > 0 ? symbolsRef.current : await loadSymbols());
      const symbolsToLoad = Array.from(new Set(rawSymbolsToLoad));
      if (symbolsToLoad.length === 0) {
        setLoading(false);
        setRefreshing(false);
        setError("No symbols available for terminal feed.");
        return;
      }

      if (!symbolsToLoad.includes(selectedSymbol)) {
        if (symbolsToLoad[0]) setSelectedSymbol(symbolsToLoad[0]);
      }

      const targetSymbol = symbolsToLoad.includes(selectedSymbol) ? selectedSymbol : (symbolsToLoad[0] ?? "");

      symbolsRef.current = symbolsToLoad;
      setSymbols(symbolsToLoad);
      initializedRef.current = true;
      setLoading(false);
      setRefreshing(false);

      const [bulkResult, singleResult] = await Promise.allSettled([
        intelligenceApi.getBulkSignals(symbolsToLoad),
        intelligenceApi.getSignal(targetSymbol),
      ]);

      const bulk = bulkResult.status === "fulfilled" ? bulkResult.value : [];
      const single = singleResult.status === "fulfilled" ? singleResult.value : null;

      if (singleResult.status === "rejected") {
        console.warn("Failed to fetch selected signal (model likely not trained yet):", singleResult.reason);
      }

      setWatchlistSignals(bulk);
      setSelectedSignal(single);
    },
    [loadSymbols, selectedSymbol]
  );

  const refreshSelected = useCallback(
    async (background = true): Promise<void> => {
      if (!selectedSymbol) {
        return;
      }
      if (background && initializedRef.current) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);
      try {
        const single = await intelligenceApi.getSignal(selectedSymbol);
        setSelectedSignal(single);
        initializedRef.current = true;
      } catch (err) {
        console.warn("Failed to fetch selected signal (model likely not trained yet):", err);
        setSelectedSignal(null);
        initializedRef.current = true;
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [selectedSymbol]
  );

  const refresh = useCallback(async (): Promise<void> => {
    await refreshAll(true);
  }, [refreshAll]);

  useEffect(() => {
    let mounted = true;
    void (async () => {
      const loaded = await loadSymbols();
      if (!mounted) {
        return;
      }
      await refreshAll(false, loaded);
    })();

    return () => {
      mounted = false;
    };
  }, [loadSymbols, refreshAll]);

  useEffect(() => {
    if (!initializedRef.current || !selectedSymbol) {
      return;
    }
    void refreshSelected(true);
  }, [refreshSelected, selectedSymbol]);

  useEffect(() => {
    if (liveSignals.size === 0) {
      return;
    }

    setWatchlistSignals((prev) =>
      prev.map((item) => {
        const incoming = liveSignals.get(item.symbol.toUpperCase());
        if (!incoming) {
          return item;
        }
        return {
          ...item,
          timestamp: incoming.timestamp,
          ensemble: {
            ...item.ensemble,
            signal: incoming.direction,
            direction: incoming.direction,
            confidence: incoming.confidence,
          },
        };
      })
    );

    setSelectedSignal((prev) => {
      if (!prev) {
        return prev;
      }
      const incoming = liveSignals.get(prev.symbol.toUpperCase());
      if (!incoming) {
        return prev;
      }
      return {
        ...prev,
        timestamp: incoming.timestamp,
        ensemble: {
          ...prev.ensemble,
          signal: incoming.direction,
          direction: incoming.direction,
          confidence: incoming.confidence,
        },
      };
    });
  }, [liveSignals]);

  useEffect(() => {
    if (!initializedRef.current) {
      return;
    }
    const id = setInterval(() => {
      void refreshAll(true);
    }, 120_000);

    return () => {
      clearInterval(id);
    };
  }, [refreshAll]);

  const addWatchlistSymbol = useCallback(async (symbol: string, listId: number = 0) => {
    try {
      const res = await watchlistApi.addSymbol(symbol, listId);
      if (res.symbols) {
        setWlLists((prev) => {
          const newLists = [...prev];
          newLists[listId] = res.symbols;
          return newLists;
        });
        const updatedSymbols = Array.from(new Set([...symbolsRef.current, ...res.symbols]));
        setSymbols(updatedSymbols);
        // The newly added symbol has no entry in watchlistSignals yet — without this,
        // it would show as missing/empty in the UI until the next 60s background poll.
        await refreshAll(true, updatedSymbols);
      }
    } catch (e) {
      console.error("Failed to add symbol", e);
    }
  }, [refreshAll]);

  const removeWatchlistSymbol = useCallback(async (symbol: string, listId: number = 0) => {
    try {
      const res = await watchlistApi.removeSymbol(symbol, listId);
      setWlLists((prev) => {
        const newLists = [...prev];
        newLists[listId] = res.symbols || [];
        return newLists;
      });
      // Not removing from symbols array aggressively because it might be in another list. 
      // It will just be filtered out of the view.
    } catch (e) {
      console.error("Failed to remove symbol", e);
    }
  }, [selectedSymbol]);

  return useMemo(
    () => ({
      symbols,
      wlLists,
      selectedSymbol,
      selectedSignal,
      watchlistSignals,
      loading,
      refreshing,
      signalStreamStatus,
      error,
      setSelectedSymbol,
      refresh: () => refreshAll(false),
      addWatchlistSymbol,
      removeWatchlistSymbol,
    }),
    [symbols, wlLists, selectedSymbol, selectedSignal, watchlistSignals, loading, refreshing, signalStreamStatus, error, setSelectedSymbol, refreshAll, addWatchlistSymbol, removeWatchlistSymbol]
  );
};
