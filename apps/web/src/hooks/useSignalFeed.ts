"use client";

import { useEffect, useState } from "react";
import { realtime, ConnectionStatus } from "@/lib/realtime";

export interface LiveSignalTick {
  symbol: string;
  signal: number;
  confidence: number;
  direction: "STRONG_BUY" | "BUY" | "NEUTRAL" | "SELL" | "STRONG_SELL";
  timestamp: string;
}

export interface UseSignalFeedState {
  signals: Map<string, LiveSignalTick>;
  status: ConnectionStatus;
}

const globalSignals = new Map<string, LiveSignalTick>();
const subscribers = new Set<() => void>();

let initialized = false;

function initGlobalListener() {
  if (initialized) return;
  initialized = true;
  realtime.onMessage((message) => {
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
    globalSignals.set(symbol, {
      symbol,
      signal: payload.signal,
      confidence: payload.confidence,
      direction: payload.direction,
      timestamp: message.timestamp ?? new Date().toISOString(),
    });
    
    subscribers.forEach((cb) => cb());
  });
}

export function useSignalFeed(symbols: string[]): UseSignalFeedState {
  const [localSignals, setLocalSignals] = useState(() => new Map<string, LiveSignalTick>());
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");

  useEffect(() => {
    if (symbols.length > 0) {
      realtime.subscribe(symbols);
    }
    return () => {
      if (symbols.length > 0) {
        realtime.unsubscribe(symbols);
      }
    };
  }, [JSON.stringify(symbols)]);

  useEffect(() => {
    initGlobalListener();

    const handleChange = () => {
      setLocalSignals(new Map(globalSignals));
    };

    subscribers.add(handleChange);
    handleChange();

    const unsubscribeStatus = realtime.onStatusChange((newStatus) => {
      setStatus(newStatus);
    });

    return () => {
      subscribers.delete(handleChange);
      unsubscribeStatus();
    };
  }, []);

  return { signals: localSignals, status };
}
