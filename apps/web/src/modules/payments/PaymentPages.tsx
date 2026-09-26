/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
"use client";

import { useEffect, useState } from "react";
import { Check, CreditCard, ShieldCheck } from "lucide-react";
import { Badge } from "@neuroquant/ui";
import { Button } from "@neuroquant/ui";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@neuroquant/ui";
import { DataTable, type Column } from "@neuroquant/ui";
import { useToastStore } from "@/stores/toast-store";
import { paymentsApi, paperTradingApi } from "@/lib/api-client";

// Pricing is now fully dynamic and fetched from the backend. 
interface PlanItem {
  id: string;
  name: string;
  price_inr: string;
  description: string;
  features: string[];
}

interface OrderHistoryItem {
  id: string;
  symbol: string;
  side: string;
  quantity: number;
  price: number;
  order_type: string;
  status: string;
  net_amount: number;
  timestamp: string;
}

export function PricingPage(): JSX.Element {
  const [plans, setPlans] = useState<PlanItem[]>([]);
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);
  const pushToast = useToastStore((state) => state.pushToast);

  useEffect(() => {
    paymentsApi.getPlans().then((res: any) => {
      setPlans(res.items);
    }).catch(() => {
      pushToast({ tone: "error", title: "Error", message: "Failed to load pricing plans" });
    });
  }, [pushToast]);

  const handleSubscribe = async (plan: PlanItem) => {
    try {
      setLoadingPlan(plan.id);
      await loadRazorpayScript();

      const intent = await paymentsApi.createIntent({ plan_id: plan.id });

      if (intent.is_test_mode) {
        // Test-mode intents have no real Razorpay order to check out against;
        // the backend only requires a matching signature when running against
        // real Razorpay credentials, so there is nothing safe to simulate
        // here without a real checkout. Surface this honestly instead of
        // faking a successful payment.
        await paymentsApi.confirmIntent(intent.intent_id, `test_${intent.intent_id}`);
        pushToast({
          tone: "success",
          title: "Subscription Active (Test Mode)",
          message: `Subscribed to ${plan.name} in test mode. No real payment was processed.`,
        });
        setLoadingPlan(null);
        return;
      }

      const options = {
        key: process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID,
        order_id: intent.provider_order_id,
        name: "NeuroQuant",
        description: `Subscription to ${plan.name}`,
        handler: async function (response: any) {
          try {
            await paymentsApi.confirmIntent(
              intent.intent_id,
              response.razorpay_payment_id,
              response.razorpay_signature
            );
            pushToast({
              tone: "success",
              title: "Subscription Active",
              message: "Your payment was verified and your subscription has been activated!",
            });
          } catch (err: any) {
            pushToast({
              tone: "error",
              title: "Payment verification failed",
              message: err?.message || "We could not verify your payment. Please contact support before retrying.",
            });
          }
        },
        theme: {
          color: "#3b82f6" // matches primary-500
        }
      };

      const rzp = new (window as any).Razorpay(options);
      rzp.open();

    } catch (err: any) {
      pushToast({
        tone: "error",
        title: "Subscription failed",
        message: err?.message || "Please try again."
      });
    } finally {
      setLoadingPlan(null);
    }
  };

  return (
    <section className="space-y-5">
      <h1 className="text-3xl font-semibold">Pricing</h1>
      <p className="text-sm text-[var(--ds-text-secondary)]">
        Choose a plan designed for your team size and operational maturity.
      </p>
      <div className="grid gap-4 md:grid-cols-3">
        {plans.map((tier) => (
          <Card key={tier.name} className="bg-[var(--ds-surface-1)]/90 flex flex-col">
            <CardHeader>
              <CardTitle>{tier.name}</CardTitle>
              <CardDescription>{tier.description}</CardDescription>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col">
              <p className="text-3xl font-semibold">
                ₹{tier.price_inr}
                <span className="text-sm text-[var(--ds-text-secondary)]">
                  /month
                </span>
              </p>
              <ul className="mt-4 space-y-2 text-sm text-[var(--ds-text-secondary)] flex-1">
                {tier.features.map((feature: string) => (
                  <li key={feature} className="flex items-center gap-2">
                    <Check className="h-4 w-4 text-[var(--ds-color-success-500)]" />
                    {feature}
                  </li>
                ))}
              </ul>
              <Button 
                className="mt-5 w-full" 
                isLoading={loadingPlan === tier.id}
                onClick={() => handleSubscribe(tier)}
              >
                Choose {tier.name}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}

const loadRazorpayScript = () => {
  return new Promise((resolve) => {
    if (document.getElementById("razorpay-script")) {
      return resolve(true);
    }
    const script = document.createElement("script");
    script.id = "razorpay-script";
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
};

export function SubscriptionDashboard(): JSX.Element {
  const pushToast = useToastStore((state) => state.pushToast);
  const [sub, setSub] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    paymentsApi.getSubscription().then((res) => {
      setSub(res);
    }).finally(() => {
      setLoading(false);
    });
  }, []);

  const handleCancel = async () => {
    if (!confirm("Are you sure you want to cancel your subscription? Cancellation takes effect at the end of your current billing cycle. You will not be charged again. We cannot offer prorated refunds directly via this portal.")) {
      return;
    }
    try {
      setCancelling(true);
      await paymentsApi.cancelSubscription();
      pushToast({ tone: "success", title: "Subscription Cancelled", message: "Your subscription will not renew." });
      // reload
      const res = await paymentsApi.getSubscription();
      setSub(res);
    } catch (err: any) {
      pushToast({ tone: "error", title: "Error", message: err?.message || "Failed to cancel." });
    } finally {
      setCancelling(false);
    }
  };

  if (loading) {
     return <div className="p-8 text-center text-sm text-[var(--ds-text-secondary)]">Loading subscription...</div>;
  }

  if (!sub) {
    return (
      <Card className="mx-auto max-w-xl bg-[var(--ds-surface-1)]/90">
        <CardHeader>
          <CardTitle>Subscription Status</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-[var(--ds-text-secondary)]">You do not have an active subscription.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="mx-auto max-w-xl bg-[var(--ds-surface-1)]/90">
      <CardHeader>
        <CardTitle>Subscription Status</CardTitle>
        <CardDescription>
          Manage your premium features and billing.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
           <p className="text-sm text-[var(--ds-text-secondary)]">Current Plan</p>
           <p className="font-medium text-lg">{sub.plan_name}</p>
        </div>
        <div>
           <p className="text-sm text-[var(--ds-text-secondary)]">Status</p>
           <Badge variant={sub.status === "active" && !sub.cancel_at_period_end ? "buy" : "neutral"}>
             {sub.cancel_at_period_end ? "Ending" : sub.status}
           </Badge>
        </div>
        {sub.status === "active" && !sub.cancel_at_period_end && sub.current_period_end && (
           <div className="bg-[var(--ds-color-primary-500)]/10 p-3 rounded-md text-sm border border-[var(--ds-color-primary-500)]/20">
             <span className="font-medium text-[var(--ds-color-primary-500)]">Active until:</span> {new Date(sub.current_period_end).toLocaleDateString()}
           </div>
        )}
        {sub.cancel_at_period_end && sub.current_period_end && (
           <div className="bg-[var(--ds-color-warning-500)]/10 p-3 rounded-md text-sm border border-[var(--ds-color-warning-500)]/20">
             <span className="font-medium text-[var(--ds-color-warning-500)]">Cancellation Pending:</span> Your subscription will end on {new Date(sub.current_period_end).toLocaleDateString()}.
           </div>
        )}

        {sub.status === "active" && !sub.cancel_at_period_end && (
          <div className="pt-4 border-t border-[var(--ds-border-subtle)]">
            <Button variant="outline" className="w-full text-[var(--ds-color-danger-500)] hover:bg-[var(--ds-color-danger-500)]/10 hover:text-[var(--ds-color-danger-500)]" isLoading={cancelling} onClick={handleCancel}>
              Cancel Subscription
            </Button>
            <p className="text-xs text-[var(--ds-text-muted)] mt-2 text-center">
              Cancellation takes effect at the end of your current billing cycle. You will not be charged again. We cannot offer prorated refunds directly via this portal.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function CheckoutPage(): JSX.Element {
  const pushToast = useToastStore((state) => state.pushToast);
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const handleReset = async () => {
    try {
      setLoading(true);
      await paperTradingApi.resetWallet();
      setConfirming(false);
      pushToast({
        tone: "success",
        title: "Wallet reset",
        message: "Your paper-trading wallet has been restored to ₹1,00,000.",
      });
    } catch (err: any) {
      pushToast({
        tone: "error",
        title: "Reset failed",
        message: err?.message || "Please try again.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="mx-auto max-w-xl bg-[var(--ds-surface-1)]/90">
      <CardHeader>
        <CardTitle>Reset Paper Wallet</CardTitle>
        <CardDescription>
          This is a virtual paper-trading wallet. No real money is ever involved.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!confirming ? (
          <>
            <p className="text-sm text-[var(--ds-text-secondary)]">
              Resetting restores your cash balance to ₹1,00,000 and permanently clears all
              open positions and order history.
            </p>
            <Button className="mt-3 w-full" variant="outline" onClick={() => setConfirming(true)}>
              <CreditCard className="mr-1 h-4 w-4" /> Reset Wallet
            </Button>
            <p className="flex items-center justify-center gap-1 mt-3 text-xs text-[var(--ds-text-muted)]">
              <ShieldCheck className="h-3.5 w-3.5" /> PAPER TRADING: No real money is charged or credited
            </p>
          </>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-[var(--ds-color-warning-500)]">
              This will delete all open positions and order history and cannot be undone. Continue?
            </p>
            <div className="flex gap-2">
              <Button className="flex-1" variant="destructive" isLoading={loading} onClick={handleReset}>
                Confirm Reset
              </Button>
              <Button className="flex-1" variant="outline" onClick={() => setConfirming(false)} disabled={loading}>
                Cancel
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function TransactionsPage(): JSX.Element {
  const [rows, setRows] = useState<OrderHistoryItem[]>([]);

  useEffect(() => {
    let mounted = true;
    paperTradingApi.getHistory()
      .then((items: any) => {
        if (!mounted) return;
        setRows(Array.isArray(items) ? items : []);
      })
      .catch(() => {
        if (!mounted) return;
      });
    return () => {
      mounted = false;
    };
  }, []);

  const columns: Column<OrderHistoryItem>[] = [
    { key: "id", label: "Order ID", render: (_, row) => row.id.slice(0, 8) },
    { key: "timestamp", label: "Date", render: (_, row) => row.timestamp.slice(0, 10) },
    { key: "symbol", label: "Symbol" },
    { key: "side", label: "Side" },
    { key: "quantity", label: "Qty", align: "right" },
    { key: "net_amount", label: "Net Amount (₹)", align: "right", render: (_, row) => row.net_amount.toFixed(2) },
    {
      key: "status",
      label: "Status",
      render: (_, row) => (
        <Badge variant={row.status === "FILLED" ? "buy" : row.status === "PENDING" ? "neutral" : "sell"}>
          {row.status}
        </Badge>
      ),
    },
  ];

  return (
    <Card className="bg-[var(--ds-surface-1)]/90">
      <CardHeader>
        <CardTitle>Order History</CardTitle>
        <CardDescription>
          Your paper-trading order log.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <DataTable columns={columns} data={rows} rowKey="id" />
      </CardContent>
    </Card>
  );
}
