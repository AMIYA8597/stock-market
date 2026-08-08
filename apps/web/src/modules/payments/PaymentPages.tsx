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
import { Input } from "@neuroquant/ui";
import { DataTable, type Column } from "@neuroquant/ui";
import { useToastStore } from "@/stores/toast-store";
import { paymentsApi } from "@/lib/api-client";

// Pricing is now fully dynamic and fetched from the backend. 
interface PlanItem {
  id: string;
  name: string;
  price_inr: string;
  description: string;
  features: string[];
}

interface TxItem {
  id: string;
  date: string;
  amount: string;
  method: string;
  status: "Success" | "Pending" | "Failed";
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
      
      const res = await paymentsApi.subscribe(plan.id);
      
      if (res.subscription_id.startsWith("sub_mock_")) {
         pushToast({
           tone: "success",
           title: "Mock Subscription Created",
           message: "Test mode: Subscription activated instantly."
         });
         return;
      }
      
      const options = {
        key: res.razorpay_key_id,
        subscription_id: res.subscription_id,
        name: "NeuroQuant",
        description: `Subscription to ${plan.name}`,
        handler: function (response: any) {
           pushToast({
             tone: "success",
             title: "Subscription Active",
             message: "Your subscription has been activated!"
           });
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
      setSub(res.subscription);
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
      setSub(res.subscription);
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
           <p className="font-medium text-lg">{sub.plan.name}</p>
        </div>
        <div>
           <p className="text-sm text-[var(--ds-text-secondary)]">Status</p>
           <Badge variant={sub.status === "active" ? "buy" : "neutral"}>{sub.status}</Badge>
        </div>
        {sub.status === "active" && (
           <div className="bg-[var(--ds-color-primary-500)]/10 p-3 rounded-md text-sm border border-[var(--ds-color-primary-500)]/20">
             <span className="font-medium text-[var(--ds-color-primary-500)]">Active until:</span> {new Date(sub.current_period_end).toLocaleDateString()}
           </div>
        )}
        {sub.status === "trialing" && (
           <div className="bg-[var(--nq-accent-cyan)]/10 p-3 rounded-md text-sm border border-[var(--nq-accent-cyan)]/20">
             <span className="font-medium text-[var(--nq-accent-cyan)]">Trial Active:</span> Your trial ends on {new Date(sub.current_period_end).toLocaleDateString()}.
           </div>
        )}
        {sub.status === "pending_cancellation" && (
           <div className="bg-[var(--ds-color-warning-500)]/10 p-3 rounded-md text-sm border border-[var(--ds-color-warning-500)]/20">
             <span className="font-medium text-[var(--ds-color-warning-500)]">Cancellation Pending:</span> Your subscription will end on {new Date(sub.current_period_end).toLocaleDateString()}.
           </div>
        )}
        
        {(sub.status === "active" || sub.status === "trialing") && (
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
  const [amount, setAmount] = useState<string>("499");
  const [step, setStep] = useState<"input" | "processing" | "success">("input");

  const handleCheckout = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setStep("processing");

      // 1. Create intent
      const intent = await paymentsApi.createIntent({
        amount: parseFloat(amount),
        method: "RAZORPAY",
        currency: "INR",
        description: "Wallet Top-up",
      });

      // 2. Simulate user interacting with a payment gateway
      await new Promise(resolve => setTimeout(resolve, 1500));

      // 3. Confirm intent
      await paymentsApi.confirmIntent(intent.intent_id, `paper_txn_${Date.now().toString(36)}`);
      
      setStep("success");
      pushToast({
        tone: "success",
        title: "Payment Successful",
        message: `Added ₹${amount} to your wallet.`,
      });
      
    } catch (err: any) {
      setStep("input");
      pushToast({
        tone: "error",
        title: "Payment failed",
        message: err?.message || "Please retry the checkout.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="mx-auto max-w-xl bg-[var(--ds-surface-1)]/90">
      <CardHeader>
        <CardTitle>Top Up Wallet</CardTitle>
        <CardDescription>
          Add funds to your paper-trading wallet.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {step === "input" && (
          <form className="space-y-3" onSubmit={handleCheckout}>
            <div>
              <label className="mb-1 block text-xs text-[var(--ds-text-secondary)]">
                Amount (INR)
              </label>
              <Input required type="number" min="100" value={amount} onChange={(e) => setAmount(e.target.value)} />
            </div>
            
            <Button className="w-full" isLoading={loading} type="submit">
              <CreditCard className="mr-1 h-4 w-4" /> Add Paper Funds
            </Button>
            <p className="flex items-center justify-center gap-1 mt-3 text-xs text-[var(--ds-text-muted)]">
              <ShieldCheck className="h-3.5 w-3.5" /> PAPER TRADING: No real money will be charged
            </p>
          </form>
        )}
        
        {step === "processing" && (
          <div className="flex flex-col items-center justify-center py-8 space-y-4">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-[var(--ds-border-subtle)] border-t-[var(--ds-color-primary-500)]"></div>
            <p className="text-sm font-medium text-[var(--ds-text-secondary)]">Processing Payment...</p>
          </div>
        )}

        {step === "success" && (
          <div className="flex flex-col items-center justify-center py-6 space-y-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--ds-color-success-500)]/20 text-[var(--ds-color-success-500)]">
              <Check className="h-6 w-6" />
            </div>
            <div className="text-center">
              <h3 className="text-lg font-medium">Payment Successful</h3>
              <p className="text-sm text-[var(--ds-text-secondary)]">₹{amount} has been added to your wallet.</p>
            </div>
            <Button className="w-full mt-4" variant="outline" onClick={() => {
              setStep("input");
              setAmount("499");
            }}>
              Make Another Payment
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function TransactionsPage(): JSX.Element {
  const [rows, setRows] = useState<TxItem[]>([]);

  useEffect(() => {
    let mounted = true;
    paymentsApi.history(20)
      .then((response: any) => {
        if (!mounted) return;
        setRows(
          (response.items || []).map((item: any) => ({
            id: item.id.toString().slice(0, 8),
            date: item.created_at.slice(0, 10),
            amount: item.amount.toString(),
            method: item.type === "credit" ? "Credit" : "Debit",
            status: "Success",
          }))
        );
      })
      .catch(() => {
        if (!mounted) return;
      });
    return () => {
      mounted = false;
    };
  }, []);

  const columns: Column<TxItem>[] = [
    { key: "id", label: "Ref" },
    { key: "date", label: "Date" },
    { key: "amount", label: "Amount", align: "right" },
    { key: "method", label: "Type" },
    {
      key: "status",
      label: "Status",
      render: (_, row) => (
        <Badge
          variant={
            row.status === "Success"
              ? "buy"
              : row.status === "Pending"
                ? "neutral"
                : "sell"
          }
        >
          {row.status}
        </Badge>
      ),
    },
  ];

  return (
    <Card className="bg-[var(--ds-surface-1)]/90">
      <CardHeader>
        <CardTitle>Wallet Ledger</CardTitle>
        <CardDescription>
          Track payment credits and subscription debits.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <DataTable columns={columns} data={rows} rowKey="id" />
      </CardContent>
    </Card>
  );
}
