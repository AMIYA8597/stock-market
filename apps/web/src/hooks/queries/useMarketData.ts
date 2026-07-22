import { useQuery } from "@tanstack/react-query";
import { marketApi } from "@/lib/api-client";

export const MARKET_DATA_QUERY_KEY = ["market-data"] as const;

export function useQuotesQuery(symbols: string[]) {
  return useQuery({
    queryKey: [...MARKET_DATA_QUERY_KEY, "quotes", symbols],
    queryFn: () => marketApi.getQuotes(symbols),
    enabled: symbols.length > 0,
    staleTime: 60 * 1000, // 1 minute
    refetchInterval: 60 * 1000, // Polling for live data
  });
}

export function useHistoryQuery(symbol: string, interval = "1d", start?: string, end?: string) {
  return useQuery({
    queryKey: [...MARKET_DATA_QUERY_KEY, "history", symbol, interval, start, end],
    queryFn: () => marketApi.getHistory(symbol, interval, start, end),
    enabled: Boolean(symbol),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
