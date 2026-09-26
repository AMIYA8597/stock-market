"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { paymentsApi } from "@/lib/api-client";
import { CheckoutPage, TransactionsPage } from "@/modules/payments/PaymentPages";
import { AuthGuard } from "@/components/auth/AuthGuard";

const moneyFormatter = new Intl.NumberFormat("en-IN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatMoney(value: number | string): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) return "INR --";
  return `INR ${moneyFormatter.format(num)}`;
}

export default function PortfolioFundsPage(): JSX.Element {
  const { data: balance } = useQuery({
    queryKey: ["payments", "balance"],
    queryFn: () => paymentsApi.balance(),
  });

  return (
    <AuthGuard>
    <main className="min-h-screen bg-[var(--nq-bg-base)] p-6 text-[var(--nq-text-primary)]">
      <div className="mb-6 flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Funds & Wallet</h1>
          <p className="text-xs text-[var(--nq-text-secondary)]">Add funds securely before placing trades via Razorpay.</p>
        </div>
        <Link
          href="/portfolio"
          className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1.5 text-xs text-[var(--nq-text-secondary)] hover:border-[var(--nq-border-hover)]"
        >
          Back to Portfolio
        </Link>
      </div>

      <section className="grid gap-6 lg:grid-cols-[1.2fr_1fr] mb-6">
        <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4 flex flex-col justify-center text-center">
          <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Available Margin / Cash Balance</h2>
          <p className="text-4xl font-semibold text-[var(--nq-text-primary)] tracking-tight">
            {balance?.wallet_balance ? formatMoney(balance.wallet_balance) : "INR 0.00"}
          </p>
          <p className="mt-2 text-xs text-[var(--nq-text-secondary)]">Cash available for placing new orders.</p>
        </article>

        <div className="flex items-center justify-center">
          <div className="w-full">
            <CheckoutPage />
          </div>
        </div>
      </section>

      <section className="mt-6">
        <TransactionsPage />
      </section>
    </main>
    </AuthGuard>
  );
}
