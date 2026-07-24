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
  const pushToast = useToastStore((state) => state.pushToast);

  useEffect(() => {
    paymentsApi.getPlans().then((res: any) => {
      setPlans(res.items);
    }).catch(() => {
      pushToast({ tone: "error", title: "Error", message: "Failed to load pricing plans" });
    });
  }, [pushToast]);

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
              <Button className="mt-5 w-full">Choose {tier.name}</Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}

export function CheckoutPage(): JSX.Element {
  const pushToast = useToastStore((state) => state.pushToast);
  const [loading, setLoading] = useState(false);
  const [amount, setAmount] = useState<string>("499");

  const handleCheckout = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const intent = await paymentsApi.createIntent({
        amount: parseFloat(amount),
        method: "RAZORPAY",
        currency: "INR",
        description: "Wallet Top-up",
      });

      // Normally here you'd open Razorpay Checkout:
      // const options = {
      //   key: intent.razorpay_key_id,
      //   amount: parseFloat(intent.amount) * 100,
      //   currency: intent.currency,
      //   order_id: intent.provider_ref,
      //   handler: async (response) => {
      //      await paymentsApi.confirmIntent(intent.intent_id, response.razorpay_payment_id, ...);
      //   }
      // }
      // const rzp = new (window as any).Razorpay(options);
      // rzp.open();
      
      // Removed success state to ensure truthful system state
      pushToast({
        tone: "error",
        title: "Payment Gateway Offline",
        message: "Razorpay SDK not loaded in this environment.",
      });
    } catch {
      pushToast({
        tone: "error",
        title: "Payment failed",
        message: "Please retry the checkout.",
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
          Add funds to your wallet using Razorpay.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-3" onSubmit={handleCheckout}>
          <div>
            <label className="mb-1 block text-xs text-[var(--ds-text-secondary)]">
              Amount (INR)
            </label>
            <Input required type="number" min="100" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </div>
          
          <Button className="w-full" isLoading={loading} type="submit">
            <CreditCard className="mr-1 h-4 w-4" /> Pay with Razorpay
          </Button>
          <p className="flex items-center justify-center gap-1 mt-3 text-xs text-[var(--ds-text-muted)]">
            <ShieldCheck className="h-3.5 w-3.5" /> TEST MODE: No real money will be charged
          </p>
        </form>
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
