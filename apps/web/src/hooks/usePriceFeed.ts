"use client";

import { useEffect, useState } from "react";
import { getWsBaseUrl } from "@/lib/runtime-config";

export interface LivePriceTick {
  symbol: string;
  price: number;
  change_pct: number;
  volume?: number;
  timestamp: string;
  source?: string;
}

type ConnectionStatus = "connected" | "reconnecting" | "disconnected";

// Singleton state
let ws: WebSocket | null = null;
let status: ConnectionStatus = "disconnected";
const ticks = new Map<string, LivePriceTick>();
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
  const wsUrl = base.endsWith("/ws") ? `${base}/prices` : `${base}/ws/prices`;
  
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
      if (message.type !== "tick") return;
      
      const payload = message.payload || {};
      if (!message.symbol || typeof payload.price !== "number") return;
      
      const symbol = message.symbol.toUpperCase();
      ticks.set(symbol, {
        symbol,
        price: payload.price,
        change_pct: payload.change_pct ?? 0,
        timestamp: message.timestamp ?? new Date().toISOString(),
        source: message.source,
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

export interface UsePriceFeedState {
  ticks: Map<string, LivePriceTick>;
  status: ConnectionStatus;
}

export function usePriceFeed(symbols: string[]): UsePriceFeedState {
  // Local state mirrored from singleton
  const [localTicks, setLocalTicks] = useState(new Map(ticks));
  const [localStatus, setLocalStatus] = useState(status);

  // Re-run whenever the required symbols list changes
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (symbols.length > 0) {
      updateSubscriptions(symbols);
    }
  }, [JSON.stringify(symbols)]);

  useEffect(() => {
    // Subscribe to singleton updates
    const handleChange = () => {
      setLocalTicks(new Map(ticks));
      setLocalStatus(status);
    };

    subscribers.add(handleChange);
    handleChange(); // Initial sync
    
    if (!ws) {
      connectWs();
    }

    return () => {
      subscribers.delete(handleChange);
      // Optional: We do not aggressively clean up symbols from the singleton on unmount
      // to avoid thrashing the WebSocket when navigating between pages.
    };
  }, []);

  return { ticks: localTicks, status: localStatus };
}
