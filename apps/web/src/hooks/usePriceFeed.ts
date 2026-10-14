"use client";

import { useEffect, useState } from "react";
import { realtime, ConnectionStatus, isWsEnvelope } from "@/lib/realtime";

export interface LivePriceTick {
  symbol: string;
  price: number;
  change_pct: number;
  volume?: number;
  timestamp: string;
  source?: string;
}

export interface UsePriceFeedState {
  ticks: Map<string, LivePriceTick>;
  status: ConnectionStatus;
}

const globalTicks = new Map<string, LivePriceTick>();
const subscribers = new Set<() => void>();

let initialized = false;

function initGlobalListener() {
  if (initialized) return;
  initialized = true;
  realtime.onMessage((raw) => {
    if (!isWsEnvelope(raw) || raw.type !== "tick") return;

    const payload = raw.payload ?? {};
    if (!raw.symbol || typeof payload.price !== "number" || typeof raw.ts !== "string") return;

    const symbol = raw.symbol.toUpperCase();
    globalTicks.set(symbol, {
      symbol,
      price: payload.price,
      change_pct: typeof payload.change_pct === "number" ? payload.change_pct : 0,
      timestamp: raw.ts,
      source: raw.source,
    });

    subscribers.forEach((cb) => cb());
  });
}

export function usePriceFeed(symbols: string[]): UsePriceFeedState {
  const [localTicks, setLocalTicks] = useState(() => new Map<string, LivePriceTick>());
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
      setLocalTicks(new Map(globalTicks));
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

  return { ticks: localTicks, status };
}
