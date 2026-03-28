"use client";

import { useEffect, useState } from "react";

import type { PortfolioTransactionResponse } from "@/lib/contracts-api";

const STORAGE_KEY = "nq-order-history-v1";

export interface OrderHistoryItem extends PortfolioTransactionResponse {
  source: "api" | "local";
}

function parseOrders(payload: string | null): OrderHistoryItem[] {
  if (!payload) {
    return [];
  }

  try {
    const parsed = JSON.parse(payload);
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed
      .filter((item) => typeof item === "object" && item !== null)
      .map((item) => item as OrderHistoryItem)
      .filter((item) => typeof item.symbol === "string" && typeof item.transaction_id === "string");
  } catch {
    return [];
  }
}

export function useOrderHistory(): {
  orders: OrderHistoryItem[];
  addOrder: (order: PortfolioTransactionResponse, source?: "api" | "local") => void;
  clearOrders: () => void;
} {
  const [orders, setOrders] = useState<OrderHistoryItem[]>([]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const loaded = parseOrders(window.localStorage.getItem(STORAGE_KEY));
    setOrders(loaded);
  }, []);

  const persist = (next: OrderHistoryItem[]): void => {
    setOrders(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    }
  };

  const addOrder = (order: PortfolioTransactionResponse, source: "api" | "local" = "api"): void => {
    const normalized: OrderHistoryItem = {
      ...order,
      symbol: order.symbol.toUpperCase(),
      type: order.type.toUpperCase() as "BUY" | "SELL",
      source,
    };
    setOrders((prev) => {
      const next = [normalized, ...prev].slice(0, 150);
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      }
      return next;
    });
  };

  const clearOrders = (): void => {
    persist([]);
  };

  return { orders, addOrder, clearOrders };
}
