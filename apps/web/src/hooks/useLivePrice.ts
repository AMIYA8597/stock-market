"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getWsBaseUrl } from "@/lib/runtime-config";

export interface LiveSignalInfo {
  direction: string;
  confidence: number;
  kelly: number;
}

interface UseLivePriceState {
  price: number | null;
  change: number | null;
  changePct: number | null;
  volume: number | null;
  signal: LiveSignalInfo | null;
  loading: boolean;
  connected: boolean;
}

const cleanWsUrl = getWsBaseUrl();

export function useLivePrice(symbol: string): UseLivePriceState {
  const [price, setPrice] = useState<number | null>(null);
  const [change, setChange] = useState<number | null>(null);
  const [changePct, setChangePct] = useState<number | null>(null);
  const [volume, setVolume] = useState<number | null>(null);
  const [signal, setSignal] = useState<LiveSignalInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [connected, setConnected] = useState<boolean>(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectDelayRef = useRef<number>(1000);

  const clearReconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const clearPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  // Poll fallback method
  const pollFallback = useCallback(async () => {
    try {
      // 1. Fetch Quote
      const quoteRes = await fetch(`/api/v1/market/quote/${encodeURIComponent(symbol)}`);
      if (quoteRes.ok) {
        const quote = await quoteRes.json();
        setPrice(Number(quote.price));
        setChange(Number(quote.change));
        setChangePct(Number(quote.change_pct));
        setVolume(Number(quote.volume));
      }

      // 2. Fetch Signal
      const signalRes = await fetch(`/api/v1/signals/${encodeURIComponent(symbol)}`);
      if (signalRes.ok) {
        const sig = await signalRes.json();
        if (sig && sig.ensemble) {
          setSignal({
            direction: sig.ensemble.direction,
            confidence: Number(sig.ensemble.confidence),
            kelly: Number(sig.ensemble.kelly_fraction || sig.ensemble.kelly || 0),
          });
        }
      }
      setLoading(false);
    } catch (err) {
      console.warn("Polling fallback failed:", err);
    }
  }, [symbol]);

  const connect = useCallback(() => {
    clearReconnect();
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    setConnected(false);
    const base = cleanWsUrl.replace(/\/+$/, "");
    const cleanBase = base.replace(/\/ws$/i, "");
    const wsUrl = `${cleanBase}/ws/live/${encodeURIComponent(symbol)}`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setLoading(false);
      reconnectDelayRef.current = 1000;
      clearPolling();
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "price_update") {
          setPrice(payload.price);
          setChangePct(payload.change_pct);
          if (payload.change !== undefined) {
            setChange(payload.change);
          }
          if (payload.volume !== undefined) {
            setVolume(payload.volume);
          }
        } else if (payload.type === "signal_update") {
          setSignal({
            direction: payload.direction,
            confidence: payload.confidence,
            kelly: payload.kelly || 0,
          });
        }
      } catch (e) {
        // ignore malformed payloads
      }
    };

    ws.onclose = () => {
      setConnected(false);
      // Start polling fallback while disconnected
      clearPolling();
      pollTimerRef.current = setInterval(pollFallback, 30000);
      pollFallback(); // Trigger immediately

      reconnectTimerRef.current = setTimeout(() => {
        reconnectDelayRef.current = Math.min(reconnectDelayRef.current * 2, 30000);
        connect();
      }, reconnectDelayRef.current);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [symbol, clearReconnect, clearPolling, pollFallback]);

  useEffect(() => {
    setLoading(true);
    connect();

    return () => {
      clearReconnect();
      clearPolling();
      setConnected(false);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [symbol, connect, clearReconnect, clearPolling]);

  return {
    price,
    change,
    changePct,
    volume,
    signal,
    loading,
    connected,
  };
}
