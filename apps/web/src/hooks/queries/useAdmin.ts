import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/lib/api-client";

export const ADMIN_QUERY_KEY = ["admin"] as const;

export function useAdminUsersQuery() {
  return useQuery({
    queryKey: [...ADMIN_QUERY_KEY, "users"],
    queryFn: () => adminApi.listUsers(),
  });
}

export function useAdminContentQuery() {
  return useQuery({
    queryKey: [...ADMIN_QUERY_KEY, "content"],
    queryFn: () => adminApi.getContent(),
  });
}
