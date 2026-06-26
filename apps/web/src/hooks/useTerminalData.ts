"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { contractsApi } from "@/lib/contracts-api";
import { intelligenceApi } from "@/lib/intelligence-api";
import { useSignalFeed } from "@/hooks/useSignalFeed";
import type { SignalResponse } from "@/types/intelligence";

const FALLBACK_SYMBOLS = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS"];

interface TerminalDataState {
  symbols: string[];
  selectedSymbol: string;
  selectedSignal: SignalResponse | null;
  watchlistSignals: SignalResponse[];
  loading: boolean;
  refreshing: boolean;
  signalStreamStatus: "connected" | "reconnecting" | "disconnected";
  error: string | null;
  setSelectedSymbol: (symbol: string) => void;
  refresh: () => Promise<void>;
}

export const useTerminalData = (): TerminalDataState => {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string>(FALLBACK_SYMBOLS[0] ?? "RELIANCE.NS");
  const [selectedSignal, setSelectedSignal] = useState<SignalResponse | null>(null);
  const [watchlistSignals, setWatchlistSignals] = useState<SignalResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const initializedRef = useRef<boolean>(false);
  const { signals: liveSignals, status: signalStreamStatus } = useSignalFeed(symbols);

  const loadSymbols = useCallback(async (): Promise<string[]> => {
    try {
      const movers = await contractsApi.getMovers("NSE", "momentum");
      const dynamicSymbols = Array.isArray(movers)
        ? movers.map((item) => item.ticker.trim().toUpperCase()).filter((item) => item.length > 0).slice(0, 12)
        : [];
      if (dynamicSymbols.length > 0) {
        setSymbols(dynamicSymbols);
        return dynamicSymbols;
      }
    } catch {
      // Fall through to explicit fallback symbols if contract is unavailable.
    }

    setSymbols(FALLBACK_SYMBOLS);
    return FALLBACK_SYMBOLS;
  }, []);

  const refreshAll = useCallback(
    async (background = false, sourceSymbols?: string[]): Promise<void> => {
      if (background && initializedRef.current) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);
      const symbolsToLoad = sourceSymbols ?? (symbols.length > 0 ? symbols : await loadSymbols());
      if (symbolsToLoad.length === 0) {
        setLoading(false);
        setRefreshing(false);
        setError("No symbols available for terminal feed.");
        return;
      }

      if (!symbolsToLoad.includes(selectedSymbol)) {
        setSelectedSymbol(symbolsToLoad[0] ?? "RELIANCE.NS");
      }

      const targetSymbol = symbolsToLoad.includes(selectedSymbol) ? selectedSymbol : (symbolsToLoad[0] ?? "RELIANCE.NS");

      try {
        const [bulk, single] = await Promise.all([
          intelligenceApi.getBulkSignals(symbolsToLoad),
          intelligenceApi.getSignal(targetSymbol),
        ]);

        setSymbols(symbolsToLoad);
        setWatchlistSignals(bulk);
        setSelectedSignal(single);
        initializedRef.current = true;
      } catch (err) {
        console.warn("Failed to fetch live signal feed:", err);
        setSymbols(symbolsToLoad);
        setWatchlistSignals([]);
        setSelectedSignal(null);
        initializedRef.current = true;
        setError("Live signal feed is unavailable. Check the backend market and signal services.");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [loadSymbols, selectedSymbol, symbols]
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
        console.warn("Failed to fetch live selected signal:", err);
        setSelectedSignal(null);
        initializedRef.current = true;
        setError("Live signal feed is unavailable. Check the backend market and signal services.");
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
    }, 60_000);

    return () => {
      clearInterval(id);
    };
  }, [refreshAll]);

  return useMemo(
    () => ({
      symbols,
      selectedSymbol,
      selectedSignal,
      watchlistSignals,
      loading,
      refreshing,
      signalStreamStatus,
      error,
      setSelectedSymbol,
      refresh,
    }),
    [symbols, selectedSymbol, selectedSignal, watchlistSignals, loading, refreshing, signalStreamStatus, error, setSelectedSymbol, refresh]
  );
};
