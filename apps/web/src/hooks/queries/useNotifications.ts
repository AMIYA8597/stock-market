import { useQuery } from "@tanstack/react-query";
import { notificationsApi } from "@/lib/api-client";

export const NOTIFICATIONS_QUERY_KEY = ["notifications"] as const;

export function useNotificationsQuery() {
  return useQuery({
    queryKey: NOTIFICATIONS_QUERY_KEY,
    queryFn: () => notificationsApi.list(),
    refetchInterval: 60 * 1000, // Background polling every minute
  });
}
