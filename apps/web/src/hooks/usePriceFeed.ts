"use client";

import { useSymbolFeed } from "@/hooks/useSymbolFeed";

export interface LivePriceTick {
  symbol: string;
  price: number;
  change_pct: number;
  volume?: number;
  timestamp: string;
  source?: string;
}

interface UsePriceFeedState {
  ticks: Map<string, LivePriceTick>;
  status: "connected" | "reconnecting" | "disconnected";
}

function parseTick(raw: unknown): LivePriceTick | null {
  const payload = raw as {
    type?: string;
    symbol?: string;
    price?: number;
    change_pct?: number;
    timestamp?: string;
    source?: string;
  };
  if (payload.type !== "tick" || !payload.symbol || typeof payload.price !== "number") {
    return null;
  }
  return {
    symbol: payload.symbol.toUpperCase(),
    price: payload.price,
    change_pct: payload.change_pct ?? 0,
    timestamp: payload.timestamp ?? new Date().toISOString(),
    source: payload.source,
  };
}

export function usePriceFeed(symbols: string[]): UsePriceFeedState {
  const { entries, status } = useSymbolFeed<LivePriceTick>(symbols, {
    path: "prices",
    parse: parseTick,
  });
  return { ticks: entries, status };
}
