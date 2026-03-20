"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

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

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

export function usePriceFeed(symbols: string[]): UsePriceFeedState {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelayRef = useRef<number>(1000);
  const [ticks, setTicks] = useState<Map<string, LivePriceTick>>(new Map());
  const [status, setStatus] = useState<"connected" | "reconnecting" | "disconnected">("disconnected");

  const normalizedSymbols = useMemo(
    () => symbols.map((s) => s.toUpperCase()).sort(),
    [symbols],
  );

  const clearReconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    clearReconnect();
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      return;
    }

    setStatus("reconnecting");
    const ws = new WebSocket(`${WS_URL}/ws/prices`);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      reconnectDelayRef.current = 1000;
      if (normalizedSymbols.length > 0) {
        ws.send(JSON.stringify({ action: "subscribe", symbols: normalizedSymbols }));
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
  }, [clearReconnect, normalizedSymbols]);

  useEffect(() => {
    connect();

    return () => {
      clearReconnect();
      setStatus("disconnected");
      if (wsRef.current) {
        wsRef.current.close();
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
  }, [normalizedSymbols]);

  return { ticks, status };
}
