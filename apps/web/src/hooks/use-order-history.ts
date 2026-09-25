"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
      return (data as any[]).map(o => ({
        ...o,
        source: 'api',
        type: o.side || o.type,
      })) as OrderHistoryItem[];
    },
  });

  const addOrder = (order: any, source: string = "api") => {
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
