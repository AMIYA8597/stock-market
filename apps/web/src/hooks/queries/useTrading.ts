import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tradingApi } from "@/lib/api-client";
import { useTradingStore } from "@/stores/tradingStore";

export const TRADING_QUERY_KEY = ["trading"] as const;
export const TRADING_AUDIT_LOG_KEY = [...TRADING_QUERY_KEY, "audit-log"] as const;
export const TRADING_MODE_KEY = [...TRADING_QUERY_KEY, "mode"] as const;
export const BROKER_STATUS_KEY = [...TRADING_QUERY_KEY, "broker-status"] as const;

export function useTradingModeQuery() {
  const setTradingModeStore = useTradingStore((state) => state.setTradingMode);
  
  return useQuery({
    queryKey: TRADING_MODE_KEY,
    queryFn: async () => {
      const res = await tradingApi.getMode();
      // Synchronize Zustand client state with server state
      setTradingModeStore(res.mode.toUpperCase() as "PAPER" | "LIVE");
      return res;
    },
  });
}

// Real Upstox broker/WebSocket connection state, from the backend's Upstox
// status endpoint (tradingApi.getUpstoxAuthStatus). The trading-mode endpoint
// says nothing about the broker, so it must not drive a connection badge.
export function useBrokerStatusQuery() {
  return useQuery({
    queryKey: BROKER_STATUS_KEY,
    queryFn: () => tradingApi.getUpstoxAuthStatus(),
    refetchInterval: 30 * 1000,
    retry: 1,
  });
}

export function useAuditLogsQuery(limit = 50) {
  return useQuery({
    queryKey: [...TRADING_AUDIT_LOG_KEY, limit],
    queryFn: () => tradingApi.getAuditLog(limit),
    refetchInterval: 10 * 1000, // Background polling for audit logs
  });
}

export function useTriggerKillSwitchMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => tradingApi.triggerKillSwitch(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: TRADING_MODE_KEY });
      queryClient.invalidateQueries({ queryKey: TRADING_AUDIT_LOG_KEY });
    },
  });
}
