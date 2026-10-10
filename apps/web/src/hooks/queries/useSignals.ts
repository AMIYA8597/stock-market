import { useQuery } from "@tanstack/react-query";
import { intelligenceApi } from "@/lib/intelligence-api";

export const SIGNALS_QUERY_KEY = ["signals"] as const;

export function useSignalQuery(symbol: string) {
  return useQuery({
    queryKey: [...SIGNALS_QUERY_KEY, symbol],
    queryFn: () => intelligenceApi.getSignal(symbol),
    enabled: Boolean(symbol),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 5 * 60 * 1000,
    retry: 1,
  });
}
