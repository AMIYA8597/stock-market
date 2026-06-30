"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getWsBaseUrl } from "@/lib/runtime-config";

export interface LivePriceTick {
  symbol: string;
  price: number;
  change_pct: number;
  timestamp: string;
}

interface UsePriceFeedState {
  ticks: Map<string, LivePriceTick>;
  status: "connected" | "reconnecting" | "disconnected";
}

const cleanWsUrl = getWsBaseUrl();

export function usePriceFeed(symbols: string[]): UsePriceFeedState {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelayRef = useRef<number>(1000);
  const [ticks, setTicks] = useState<Map<string, LivePriceTick>>(new Map());
  const [status, setStatus] = useState<"connected" | "reconnecting" | "disconnected">("disconnected");

  const serializedSymbols = JSON.stringify(symbols.map((s) => s.toUpperCase()).sort());
  const normalizedSymbols = useMemo(
    () => JSON.parse(serializedSymbols) as string[],
    [serializedSymbols],
  );
  const symbolsRef = useRef(normalizedSymbols);
  useEffect(() => {
    symbolsRef.current = normalizedSymbols;
  }, [normalizedSymbols]);

  const clearReconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    clearReconnect();
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    setStatus("reconnecting");
    const base = cleanWsUrl.replace(/\/+$/, "");
    const wsUrl = base.endsWith("/ws") ? `${base}/prices` : `${base}/ws/prices`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      reconnectDelayRef.current = 1000;
      if (symbolsRef.current.length > 0) {
        ws.send(JSON.stringify({ action: "subscribe", symbols: symbolsRef.current }));
      }
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data as string) as {
          type?: string;
          symbol?: string;
          price?: number;
          change_pct?: number;
          timestamp?: string;
        };
        if (payload.type !== "tick" || !payload.symbol || typeof payload.price !== "number") {
          return;
        }
        const symbol = payload.symbol.toUpperCase();
        const price = payload.price;
        setTicks((prev) => {
          const next = new Map(prev);
          next.set(symbol, {
            symbol,
            price,
            change_pct: payload.change_pct ?? 0,
            timestamp: payload.timestamp ?? new Date().toISOString(),
          });
          return next;
        });
      } catch {
        // Ignore malformed payloads.
      }
    };

    ws.onclose = () => {
      setStatus("reconnecting");
      reconnectTimerRef.current = setTimeout(() => {
        reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 2, 30000);
        connect();
      }, reconnectDelayRef.current);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [clearReconnect]);

  useEffect(() => {
    connect();

    return () => {
      clearReconnect();
      setStatus("disconnected");
      if (wsRef.current) {
        const ws = wsRef.current;
        if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
          ws.close();
        }
        wsRef.current = null;
      }
    };
  }, [connect, clearReconnect]);

  useEffect(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return;
    }
    ws.send(JSON.stringify({ action: "subscribe", symbols: normalizedSymbols }));
  }, [serializedSymbols, normalizedSymbols]);

  return { ticks, status };
}
