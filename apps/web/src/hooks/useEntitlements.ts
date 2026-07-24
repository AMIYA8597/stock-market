/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
import { useEffect, useState } from "react";
import { paymentsApi } from "@/lib/api-client";
import { useToastStore } from "@/stores/toast-store";
import { getApiBaseUrl } from "@/lib/runtime-config";

export interface SubscriptionContext {
  subscription: {
    id: string;
    status: string;
    current_period_end: string;
    plan: {
      name: string;
      features: string[];
    };
  } | null;
  loading: boolean;
  error: Error | null;
}

export function useEntitlements(): SubscriptionContext {
  const [context, setContext] = useState<SubscriptionContext>({
    subscription: null,
    loading: true,
    error: null,
  });

  useEffect(() => {
    let mounted = true;
    const fetchSubscription = async () => {
      try {
        const token = localStorage.getItem("nq_access_token");
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }
        
        const res = await fetch(`${getApiBaseUrl()}/api/v1/payments/subscription`, {
          headers
        });
        
        if (!res.ok) {
          throw new Error("Failed to fetch subscription");
        }
        
        const data = await res.json();
        if (mounted) {
          setContext({
            subscription: data.subscription,
            loading: false,
            error: null,
          });
        }
      } catch (err: any) {
        if (mounted) {
          setContext({
            subscription: null,
            loading: false,
            error: err,
          });
        }
      }
    };

    fetchSubscription();
    return () => {
      mounted = false;
    };
  }, []);

  return context;
}
