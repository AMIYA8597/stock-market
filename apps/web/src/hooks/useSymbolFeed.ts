"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getWsBaseUrl } from "@/lib/runtime-config";

export type FeedStatus = "connected" | "reconnecting" | "disconnected";

export interface SymbolFeedState<T> {
  entries: Map<string, T>;
  status: FeedStatus;
}

interface SymbolFeedOptions<T> {
  /** Path appended to the websocket base URL, e.g. "prices" or "signals". */
  path: string;
  /** Maps a raw websocket payload to a feed entry, or null when it should be ignored. */
  parse: (payload: unknown) => T | null;
}

const WS_BASE_URL = getWsBaseUrl();
const INITIAL_RECONNECT_DELAY_MS = 1000;
const MAX_RECONNECT_DELAY_MS = 30000;

/**
 * Subscribes to a symbol-keyed websocket feed, keeping the latest entry per symbol
 * and reconnecting with exponential backoff.
 */
export function useSymbolFeed<T extends { symbol: string }>(
  symbols: string[],
  { path, parse }: SymbolFeedOptions<T>,
): SymbolFeedState<T> {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectDelayRef = useRef<number>(INITIAL_RECONNECT_DELAY_MS);
  const parseRef = useRef(parse);
  const [entries, setEntries] = useState<Map<string, T>>(new Map());
  const [status, setStatus] = useState<FeedStatus>("disconnected");

  useEffect(() => {
    parseRef.current = parse;
  }, [parse]);

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
    if (
      wsRef.current &&
      (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    setStatus("reconnecting");
    const base = WS_BASE_URL.replace(/\/+$/, "").replace(/\/ws$/i, "");
    const ws = new WebSocket(`${base}/ws/${path}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      reconnectDelayRef.current = INITIAL_RECONNECT_DELAY_MS;
      if (symbolsRef.current.length > 0) {
        ws.send(JSON.stringify({ action: "subscribe", symbols: symbolsRef.current }));
      }
    };

    ws.onmessage = (event) => {
      try {
        const entry = parseRef.current(JSON.parse(event.data as string));
        if (!entry) {
          return;
        }
        setEntries((prev) => new Map(prev).set(entry.symbol, entry));
      } catch {
        // Ignore malformed payloads.
      }
    };

    ws.onclose = () => {
      setStatus("reconnecting");
      reconnectTimerRef.current = setTimeout(() => {
        reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 2, MAX_RECONNECT_DELAY_MS);
        connect();
      }, reconnectDelayRef.current);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [clearReconnect, path]);

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

  return { entries, status };
}
