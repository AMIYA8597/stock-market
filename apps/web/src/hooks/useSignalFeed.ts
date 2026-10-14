"use client";

import { useEffect, useState } from "react";
import { realtime, ConnectionStatus, isWsEnvelope } from "@/lib/realtime";

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
  realtime.onMessage((raw) => {
    if (!isWsEnvelope(raw) || (raw.type !== "signal" && raw.type !== "signal_update")) return;

    const payload = raw.payload ?? {};
    if (
      !raw.symbol ||
      typeof payload.signal !== "number" ||
      typeof payload.confidence !== "number" ||
      typeof payload.direction !== "string" ||
      typeof raw.ts !== "string"
    ) {
      return;
    }

    const symbol = raw.symbol.toUpperCase();
    globalSignals.set(symbol, {
      symbol,
      signal: payload.signal,
      confidence: payload.confidence,
      direction: payload.direction as LiveSignalTick["direction"],
      timestamp: raw.ts,
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
