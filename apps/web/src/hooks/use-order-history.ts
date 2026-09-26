"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { paperTradingApi } from "@/lib/api-client";
import type { PortfolioTransactionResponse } from "@/lib/contracts-api";

export interface OrderHistoryItem extends PortfolioTransactionResponse {
  source: "api" | "local";
}

export function useOrderHistory() {
  const queryClient = useQueryClient();

  const { data: orders = [], isLoading } = useQuery({
    queryKey: ['orders'],
    queryFn: async () => {
      const data = await paperTradingApi.getHistory();
      return (data as Array<Record<string, unknown> & { side?: string; type?: string }>).map(o => ({
        ...o,
        source: 'api',
        type: o.side || o.type,
      })) as OrderHistoryItem[];
    },
  });

  // Backend order history is fetched via the `orders` query above; this hook
  // has no local order state to append to, so it only invalidates the cache
  // that already reflects the just-placed order once the backend confirms it.
  const addOrder = () => {
    // Optimistic update can go here, but for now we just invalidate
    queryClient.invalidateQueries({ queryKey: ['orders'] });
    queryClient.invalidateQueries({ queryKey: ['portfolio'] });
  };

  const clearOrders = () => {
    // If backend supports clearing history, call it. Otherwise do nothing.
    queryClient.setQueryData(['orders'], []);
  };

  return { orders, addOrder, clearOrders, isLoading };
}
