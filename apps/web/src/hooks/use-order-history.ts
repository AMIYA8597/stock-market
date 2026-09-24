"use client";

import { create } from "zustand";
import type { PortfolioTransactionResponse } from "@/lib/contracts-api";

export interface OrderHistoryItem extends PortfolioTransactionResponse {
  source: "api" | "local";
}

interface OrderHistoryStore {
  orders: OrderHistoryItem[];
  addOrder: (order: PortfolioTransactionResponse, source?: "api" | "local") => void;
  clearOrders: () => void;
}

export const useOrderHistory = create<OrderHistoryStore>((set) => ({
  orders: [],
  addOrder: (order, source = "api") => set((state) => {
    const normalized: OrderHistoryItem = {
      ...order,
      symbol: order.symbol.toUpperCase(),
      type: order.type.toUpperCase() as "BUY" | "SELL",
      source,
    };
    return { orders: [normalized, ...state.orders].slice(0, 150) };
  }),
  clearOrders: () => set({ orders: [] }),
}));
