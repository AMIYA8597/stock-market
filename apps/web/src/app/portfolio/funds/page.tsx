"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  contractsApi,
  type PaymentHistoryItem,
  type PaymentMethod,
  type PaymentIntentResponse,
} from "@/lib/contracts-api";

const moneyFormatter = new Intl.NumberFormat("en-IN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatMoney(value: number): string {
  return `INR ${moneyFormatter.format(value)}`;
}

export default function PortfolioFundsPage(): JSX.Element {
  const [methods, setMethods] = useState<PaymentMethod[]>([]);
  const [history, setHistory] = useState<PaymentHistoryItem[]>([]);
  const [walletBalance, setWalletBalance] = useState<number>(0);
  const [amount, setAmount] = useState<number>(5000);
  const [method, setMethod] = useState<PaymentMethod["code"]>("UPI");
  const [otp, setOtp] = useState<string>("000000");
  const [intent, setIntent] = useState<PaymentIntentResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load(): Promise<void> {
      setLoading(true);
      setError(null);
      const [methodsRes, balanceRes, historyRes] = await Promise.allSettled([
        contractsApi.getPaymentMethods(),
        contractsApi.getWalletBalance(),
        contractsApi.getPaymentHistory(25),
      ]);

      if (!mounted) {
        return;
      }

      if (methodsRes.status === "fulfilled") {
        setMethods(methodsRes.value.methods);
      }

      if (balanceRes.status === "fulfilled") {
        setWalletBalance(balanceRes.value.wallet_balance);
      }

      if (historyRes.status === "fulfilled") {
        setHistory(historyRes.value.items);
      }

      if (methodsRes.status === "rejected" || balanceRes.status === "rejected" || historyRes.status === "rejected") {
        setError("Unable to load payments module data.");
      }

      setLoading(false);
    }

    void load();

    return () => {
      mounted = false;
    };
  }, []);

  const selectedMethod = useMemo(
    () => methods.find((item) => item.code === method) ?? null,
    [methods, method],
  );

  async function createIntent(): Promise<void> {
    setError(null);
    setSuccess(null);

    try {
      const nextIntent = await contractsApi.createPaymentIntent({
        amount,
        method,
        currency: "INR",
        description: "Trading wallet top-up",
      });
      setIntent(nextIntent);
      setSuccess("Payment intent created. Confirm to credit wallet.");
    } catch (err) {
      setIntent(null);
      setError(err instanceof Error ? err.message : "Unable to create payment intent.");
    }
  }

  async function confirmIntent(): Promise<void> {
    if (!intent) {
      setError("Create an intent first.");
      return;
    }

    setError(null);
    setSuccess(null);

    try {
      const result = await contractsApi.confirmPaymentIntent({
        intent_id: intent.intent_id,
        confirmation_code: otp,
      });
      const [balanceRes, historyRes] = await Promise.all([
        contractsApi.getWalletBalance(),
        contractsApi.getPaymentHistory(25),
      ]);
      setWalletBalance(balanceRes.wallet_balance);
      setHistory(historyRes.items);
      setIntent(null);
      setSuccess(`Wallet credited by ${formatMoney(result.credited_amount)}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to confirm payment intent.");
    }
  }

  return (
    <main className="min-h-screen bg-[var(--nq-bg-base)] p-6 text-[var(--nq-text-primary)]">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Funds & Payments</h1>
          <p className="text-xs text-[var(--nq-text-secondary)]">Add funds securely before placing trades.</p>
        </div>
        <Link
          href="/portfolio"
          className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1.5 text-xs text-[var(--nq-text-secondary)] hover:border-[var(--nq-border-hover)]"
        >
          Back to Portfolio
        </Link>
      </div>

      {error ? <p className="mb-3 text-sm text-[var(--nq-accent-red)]">{error}</p> : null}
      {success ? <p className="mb-3 text-sm text-[var(--nq-accent-green)]">{success}</p> : null}

      <section className="grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Top-up Wallet</h2>

          <div className="mb-4 grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-xs text-[var(--nq-text-secondary)]">
              Amount (INR)
              <input
                type="number"
                min={selectedMethod?.min_amount ?? 100}
                max={selectedMethod?.max_amount ?? 200000}
                value={amount}
                onChange={(event) => setAmount(Number(event.target.value))}
                className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-base)] px-2 py-1.5 text-sm text-[var(--nq-text-primary)] outline-none focus:border-[var(--nq-accent-blue)]"
              />
            </label>

            <label className="flex flex-col gap-1 text-xs text-[var(--nq-text-secondary)]">
              Payment Method
              <select
                value={method}
                onChange={(event) => setMethod(event.target.value as PaymentMethod["code"])}
                className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-base)] px-2 py-1.5 text-sm text-[var(--nq-text-primary)] outline-none focus:border-[var(--nq-accent-blue)]"
              >
                {methods.map((item) => (
                  <option key={item.code} value={item.code}>
                    {item.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="mb-4 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-3 py-2 text-xs text-[var(--nq-text-secondary)]">
            {selectedMethod
              ? `Limits for ${selectedMethod.label}: ${formatMoney(selectedMethod.min_amount)} to ${formatMoney(selectedMethod.max_amount)}`
              : "Loading payment method limits..."}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => void createIntent()}
              disabled={loading}
              className="rounded bg-[var(--nq-accent-blue)] px-3 py-1.5 text-xs font-medium text-[#07101A] disabled:opacity-60"
            >
              Create Payment Intent
            </button>

            <input
              type="text"
              value={otp}
              onChange={(event) => setOtp(event.target.value)}
              placeholder="Confirmation code"
              className="w-40 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-base)] px-2 py-1.5 text-xs text-[var(--nq-text-primary)] outline-none focus:border-[var(--nq-accent-blue)]"
            />

            <button
              type="button"
              onClick={() => void confirmIntent()}
              disabled={!intent || loading}
              className="rounded bg-[var(--nq-accent-green)] px-3 py-1.5 text-xs font-medium text-[#07130E] disabled:opacity-60"
            >
              Confirm & Credit
            </button>
          </div>

          {intent ? (
            <div className="mt-4 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-3 py-2 text-xs text-[var(--nq-text-secondary)]">
              Intent: {intent.intent_id} | Provider Ref: {intent.provider_ref}
            </div>
          ) : null}
        </article>

        <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
          <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Wallet Balance</h2>
          <p className="text-2xl font-semibold text-[var(--nq-text-primary)]">{formatMoney(walletBalance)}</p>
          <p className="mt-2 text-xs text-[var(--nq-text-secondary)]">Available cash for orders and rebalancing.</p>
        </article>
      </section>

      <section className="mt-6 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
        <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Payment History</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead>
              <tr className="text-[var(--nq-text-secondary)]">
                <th className="pb-2 text-left font-medium">Payment ID</th>
                <th className="pb-2 text-left font-medium">Method</th>
                <th className="pb-2 text-right font-medium">Amount</th>
                <th className="pb-2 text-left font-medium">Status</th>
                <th className="pb-2 text-left font-medium">Completed</th>
              </tr>
            </thead>
            <tbody>
              {history.map((item) => (
                <tr key={item.payment_id} className="border-t border-[var(--nq-border)]">
                  <td className="py-2">{item.payment_id}</td>
                  <td className="py-2">{item.method}</td>
                  <td className="py-2 text-right">{formatMoney(item.amount)}</td>
                  <td className="py-2">{item.status}</td>
                  <td className="py-2">{item.completed_at ? new Date(item.completed_at).toLocaleString() : "--"}</td>
                </tr>
              ))}
              {!loading && history.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-3 text-[var(--nq-text-secondary)]">
                    No payment history yet.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
