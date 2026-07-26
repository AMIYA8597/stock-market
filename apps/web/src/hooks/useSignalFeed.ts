"use client";

import { useSymbolFeed } from "@/hooks/useSymbolFeed";

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

function parseSignal(raw: unknown): LiveSignalTick | null {
  const payload = raw as {
    type?: string;
    symbol?: string;
    signal?: number;
    confidence?: number;
    direction?: LiveSignalTick["direction"];
    timestamp?: string;
  };

  if (
    payload.type !== "signal_update" ||
    !payload.symbol ||
    typeof payload.signal !== "number" ||
    typeof payload.confidence !== "number" ||
    !payload.direction
  ) {
    return null;
  }

  return {
    symbol: payload.symbol.toUpperCase(),
    signal: payload.signal,
    confidence: payload.confidence,
    direction: payload.direction,
    timestamp: payload.timestamp ?? new Date().toISOString(),
  };
}

export function useSignalFeed(symbols: string[]): UseSignalFeedState {
  const { entries, status } = useSymbolFeed<LiveSignalTick>(symbols, {
    path: "signals",
    parse: parseSignal,
  });
  return { signals: entries, status };
}
