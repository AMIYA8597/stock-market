"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

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

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
const cleanWsUrl = WS_URL.endsWith("/ws") ? WS_URL.slice(0, -3) : WS_URL;

export function useSignalFeed(symbols: string[]): UseSignalFeedState {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelayRef = useRef<number>(1000);
  const [signals, setSignals] = useState<Map<string, LiveSignalTick>>(new Map());
  const [status, setStatus] = useState<"connected" | "reconnecting" | "disconnected">("disconnected");

  const normalizedSymbols = useMemo(() => symbols.map((s) => s.toUpperCase()).sort(), [symbols]);

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
    const ws = new WebSocket(`${cleanWsUrl}/ws/signals`);
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
          signal?: number;
          confidence?: number;
          direction?: "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL";
          timestamp?: string;
        };

        if (
          payload.type !== "signal_update" ||
          !payload.symbol ||
          typeof payload.signal !== "number" ||
          typeof payload.confidence !== "number" ||
          !payload.direction
        ) {
          return;
        }

        const symbol = payload.symbol.toUpperCase();
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
            timestamp: payload.timestamp ?? new Date().toISOString(),
          });
          return next;
        });
      } catch {
        // Ignore malformed websocket payloads.
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
  }, [clearReconnect, connect]);

  useEffect(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return;
    }
    ws.send(JSON.stringify({ action: "subscribe", symbols: normalizedSymbols }));
  }, [normalizedSymbols]);

  return { signals, status };
}