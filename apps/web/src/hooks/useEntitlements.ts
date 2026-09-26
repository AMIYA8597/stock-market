import { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api-client";

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
        const data = await fetchApi<{ subscription: SubscriptionContext["subscription"] }>(
          "/payments/subscription"
        );
        if (mounted) {
          setContext({
            subscription: data.subscription,
            loading: false,
            error: null,
          });
        }
      } catch (err) {
        if (mounted) {
          setContext({
            subscription: null,
            loading: false,
            error: err instanceof Error ? err : new Error(String(err)),
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
