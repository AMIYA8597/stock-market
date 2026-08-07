"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getWsBaseUrl } from "@/lib/runtime-config";

export interface LiveSignalTick {
  symbol: string;
  signal: number;
  confidence: number;
  direction: "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL";
  timestamp: string;
}

interface UseSignalFeedState {
  signals: Map<string, LiveSignalTick>;
  status: "connected" | "reconnecting" | "disconnected";
}

const cleanWsUrl = getWsBaseUrl();

export function useSignalFeed(symbols: string[]): UseSignalFeedState {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelayRef = useRef<number>(1000);
  const mountedRef = useRef<boolean>(true);
  const [signals, setSignals] = useState<Map<string, LiveSignalTick>>(new Map());
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
    const cleanBase = base.replace(/\/ws$/i, "");
    const wsUrl = `${cleanBase}/ws/signals`; // Resolved WebSocket URL: ws://host:port/ws/signals (no double slash)
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
        const message = JSON.parse(event.data as string);

        if (message.type !== "signal" && message.type !== "signal_update") {
          return;
        }
        
        const payload = message.payload || {};
        
        if (
          !message.symbol ||
          typeof payload.signal !== "number" ||
          typeof payload.confidence !== "number" ||
          !payload.direction
        ) {
          return;
        }

        const symbol = message.symbol.toUpperCase();
        const nextSignal = payload.signal;
        const nextConfidence = payload.confidence;
        const nextDirection = payload.direction;
        setSignals((prev) => {
          const next = new Map(prev);
          next.set(symbol, {
            symbol,
            signal: nextSignal,
            confidence: nextConfidence,
            direction: nextDirection,
            timestamp: message.timestamp ?? new Date().toISOString(),
          });
          return next;
        });
      } catch {
        // Ignore malformed websocket payloads.
      }
    };

    ws.onclose = () => {
      if (!mountedRef.current) return;
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
      mountedRef.current = false;
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
  }, [clearReconnect, connect]);

  useEffect(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return;
    }
    ws.send(JSON.stringify({ action: "subscribe", symbols: normalizedSymbols }));
  }, [serializedSymbols, normalizedSymbols]);

  return { signals, status };
}
