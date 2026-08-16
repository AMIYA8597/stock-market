"use client";

import { useEffect, useState } from "react";
import { getWsBaseUrl } from "@/lib/runtime-config";

export interface LiveSignalTick {
  symbol: string;
  signal: number;
  confidence: number;
  direction: "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL";
  timestamp: string;
}

type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

// Singleton state
let ws: WebSocket | null = null;
let status: ConnectionStatus = "disconnected";
const signals = new Map<string, LiveSignalTick>();
const activeSymbols = new Set<string>();
const subscribers = new Set<() => void>();
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let reconnectDelay = 1000;

function notifySubscribers() {
  subscribers.forEach((cb) => cb());
}

function connectWs() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }

  status = "reconnecting";
  notifySubscribers();

  const cleanWsUrl = getWsBaseUrl();
  const base = cleanWsUrl.replace(/\/+$/, "");
  const cleanBase = base.replace(/\/ws$/i, "");
  const wsUrl = `${cleanBase}/ws/signals`; // Resolved WebSocket URL: ws://host:port/ws/signals
  
  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    status = "connected";
    reconnectDelay = 1000;
    if (activeSymbols.size > 0) {
      ws?.send(JSON.stringify({ action: "subscribe", symbols: Array.from(activeSymbols) }));
    }
    notifySubscribers();
  };

  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data as string);
      if (message.type !== "signal" && message.type !== "signal_update") return;
      
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
      signals.set(symbol, {
        symbol,
        signal: payload.signal,
        confidence: payload.confidence,
        direction: payload.direction,
        timestamp: message.timestamp ?? new Date().toISOString(),
      });
      notifySubscribers();
    } catch {
      // ignore
    }
  };

  ws.onclose = () => {
    ws = null;
    status = "reconnecting";
    notifySubscribers();
    
    // Exponential backoff
    reconnectTimer = setTimeout(() => {
      reconnectDelay = Math.min(reconnectDelay * 2, 30000);
      connectWs();
    }, reconnectDelay);
  };

  ws.onerror = () => {
    ws?.close(); // triggers onclose
  };
}

function updateSubscriptions(symbols: string[]) {
  let changed = false;
  
  // Add new
  for (const s of symbols) {
    const sym = s.toUpperCase();
    if (!activeSymbols.has(sym)) {
      activeSymbols.add(sym);
      changed = true;
    }
  }

  if (changed && ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: "subscribe", symbols: Array.from(activeSymbols) }));
  }
  
  // Start connection if not running and we have symbols
  if (activeSymbols.size > 0 && !ws) {
    connectWs();
  }
}

export interface UseSignalFeedState {
  signals: Map<string, LiveSignalTick>;
  status: ConnectionStatus;
}

export function useSignalFeed(symbols: string[]): UseSignalFeedState {
  // Seed with the module's static defaults, not the live singleton value — see
  // usePriceFeed.ts for why (avoids a hydration mismatch when the singleton has
  // already advanced by the time a later component mounts).
  const [localSignals, setLocalSignals] = useState(() => new Map<string, LiveSignalTick>());
  const [localStatus, setLocalStatus] = useState<ConnectionStatus>("disconnected");

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (symbols.length > 0) {
      updateSubscriptions(symbols);
    }
  }, [JSON.stringify(symbols)]);

  useEffect(() => {
    const handleChange = () => {
      setLocalSignals(new Map(signals));
      setLocalStatus(status);
    };

    subscribers.add(handleChange);
    handleChange(); // Initial sync
    
    if (!ws) {
      connectWs();
    }

    return () => {
      subscribers.delete(handleChange);
    };
  }, []);

  return { signals: localSignals, status: localStatus };
}
