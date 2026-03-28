"use client";

import { useEffect, useState } from 'react';
import { Check, CreditCard, ShieldCheck } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { DataTable, type Column } from '@/components/ui/DataTable';
import { useToastStore } from '@/stores/toast-store';
import { paymentsApi } from '@/lib/api-client';

const tiers = [
  { name: 'Starter', price: '$49', description: 'Solo and small teams', features: ['3 workspaces', 'Basic analytics', 'Email support'] },
  { name: 'Growth', price: '$149', description: 'Scaling investment teams', features: ['10 workspaces', 'Advanced dashboards', 'Priority support'] },
  { name: 'Enterprise', price: 'Custom', description: 'Compliance-ready deployments', features: ['Unlimited seats', 'SAML + RBAC', 'Dedicated success manager'] },
];

interface TxItem {
  id: string;
  date: string;
  amount: string;
  method: string;
  status: 'Success' | 'Pending' | 'Failed';
}

const txRows: TxItem[] = [
  { id: 'INV-3901', date: '2026-03-24', amount: '$149.00', method: 'Visa **** 4832', status: 'Success' },
  { id: 'INV-3892', date: '2026-02-24', amount: '$149.00', method: 'Visa **** 4832', status: 'Success' },
  { id: 'INV-3883', date: '2026-01-24', amount: '$149.00', method: 'Visa **** 4832', status: 'Pending' },
  { id: 'INV-3874', date: '2025-12-24', amount: '$149.00', method: 'Visa **** 4832', status: 'Failed' },
];

export function PricingPage(): JSX.Element {
  return (
    <section className="space-y-5">
      <h1 className="text-3xl font-semibold">Pricing</h1>
      <p className="text-sm text-[var(--ds-text-secondary)]">Choose a plan designed for your team size and operational maturity.</p>
      <div className="grid gap-4 md:grid-cols-3">
        {tiers.map((tier) => (
          <Card key={tier.name} className="bg-[var(--ds-surface-1)]/90">
            <CardHeader>
              <CardTitle>{tier.name}</CardTitle>
              <CardDescription>{tier.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-semibold">{tier.price}<span className="text-sm text-[var(--ds-text-secondary)]">/month</span></p>
              <ul className="mt-4 space-y-2 text-sm text-[var(--ds-text-secondary)]">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2"><Check className="h-4 w-4 text-[var(--ds-color-success-500)]" />{feature}</li>
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
  const [intentId, setIntentId] = useState<string | null>(null);

  return (
    <Card className="mx-auto max-w-xl bg-[var(--ds-surface-1)]/90">
      <CardHeader>
        <CardTitle>Secure Checkout</CardTitle>
        <CardDescription>Encrypted payment processing with role-based billing controls.</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="space-y-3"
          onSubmit={async (event) => {
            event.preventDefault();
            try {
              setLoading(true);
              const intent = await paymentsApi.createIntent({
                amount: 149,
                method: 'CARD',
                currency: 'INR',
                description: 'Growth subscription',
              });
              setIntentId(intent.intent_id);
              await paymentsApi.confirmIntent(intent.intent_id, '123456');
              pushToast({ tone: 'success', title: 'Payment successful', message: 'Your plan has been upgraded to Growth.' });
            } catch {
              pushToast({ tone: 'error', title: 'Payment failed', message: 'Please retry the checkout.' });
            } finally {
              setLoading(false);
            }
          }}
        >
          <div>
            <label className="mb-1 block text-xs text-[var(--ds-text-secondary)]">Cardholder</label>
            <Input required placeholder="Full name" />
          </div>
          <div>
            <label className="mb-1 block text-xs text-[var(--ds-text-secondary)]">Card number</label>
            <Input required placeholder="4242 4242 4242 4242" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs text-[var(--ds-text-secondary)]">Expiry</label>
              <Input required placeholder="MM/YY" />
            </div>
            <div>
              <label className="mb-1 block text-xs text-[var(--ds-text-secondary)]">CVV</label>
              <Input required placeholder="123" />
            </div>
          </div>
          <Button className="w-full" isLoading={loading} type="submit"><CreditCard className="mr-1 h-4 w-4" /> Complete payment</Button>
          {intentId ? <p className="text-center text-xs text-[var(--ds-text-muted)]">Intent: {intentId}</p> : null}
          <p className="flex items-center justify-center gap-1 text-xs text-[var(--ds-text-muted)]"><ShieldCheck className="h-3.5 w-3.5" /> PCI compliant payment flow</p>
        </form>
      </CardContent>
    </Card>
  );
}

export function TransactionsPage(): JSX.Element {
  const [rows, setRows] = useState<TxItem[]>(txRows);

  useEffect(() => {
    let mounted = true;
    paymentsApi.history(20).then((response) => {
      if (!mounted) return;
      setRows(
        response.items.map((item) => ({
          id: item.intent_id,
          date: item.created_at.slice(0, 10),
          amount: item.amount,
          method: item.method,
          status: item.status.toLowerCase() === 'succeeded' ? 'Success' : item.status.toLowerCase() === 'failed' ? 'Failed' : 'Pending',
        }))
      );
    }).catch(() => {
      if (!mounted) return;
    });
    return () => {
      mounted = false;
    };
  }, []);

  const columns: Column<TxItem>[] = [
    { key: 'id', label: 'Invoice' },
    { key: 'date', label: 'Date' },
    { key: 'amount', label: 'Amount', align: 'right' },
    { key: 'method', label: 'Method' },
    {
      key: 'status',
      label: 'Status',
      render: (_, row) => (
        <Badge variant={row.status === 'Success' ? 'buy' : row.status === 'Pending' ? 'neutral' : 'sell'}>{row.status}</Badge>
      ),
    },
  ];

  return (
    <Card className="bg-[var(--ds-surface-1)]/90">
      <CardHeader>
        <CardTitle>Transaction History</CardTitle>
        <CardDescription>Track payment status with clear success, pending, and failure states.</CardDescription>
      </CardHeader>
      <CardContent>
        <DataTable columns={columns} data={rows} rowKey="id" />
      </CardContent>
    </Card>
  );
}
