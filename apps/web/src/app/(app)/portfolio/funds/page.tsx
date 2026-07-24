/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { paymentsApi } from "@/lib/api-client";

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
  const queryClient = useQueryClient();
  const [amount, setAmount] = useState<number>(5000);
  const [method, setMethod] = useState<string>("UPI");
  const [otp, setOtp] = useState<string>("000000");
  const [intent, setIntent] = useState<{ intent_id: string; provider_ref: string } | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const { data: methodsData, isLoading: isLoadingMethods } = useQuery({
    queryKey: ["payments", "methods"],
    queryFn: () => paymentsApi.methods(),
  });
  const methods = ((methodsData as any)?.items || (Array.isArray(methodsData) ? methodsData : [])) as any[];

  const { data: balanceData, isLoading: isLoadingBalance } = useQuery({
    queryKey: ["payments", "balance"],
    queryFn: () => paymentsApi.balance(),
  });

  const { data: historyData, isLoading: isLoadingHistory } = useQuery({
    queryKey: ["payments", "history"],
    queryFn: () => paymentsApi.history(25),
  });
  const history = ((historyData as any)?.items || (Array.isArray(historyData) ? historyData : [])) as any[];

  const selectedMethod = methods.find((item) => item.code === method) ?? null;

  const createIntentMutation = useMutation({
    mutationFn: () => paymentsApi.createIntent({ amount, method: method as any, currency: "INR", description: "Trading wallet top-up" }),
    onSuccess: (data) => {
      setIntent(data);
      setSuccessMsg("Payment intent created. Confirm to credit wallet.");
      setErrorMsg(null);
    },
    onError: (err: Error) => {
      setIntent(null);
      setErrorMsg(err.message || "Unable to create payment intent.");
      setSuccessMsg(null);
    },
  });

  const confirmIntentMutation = useMutation({
    mutationFn: () => paymentsApi.confirmIntent(intent!.intent_id, otp),
    onSuccess: (data) => {
      setIntent(null);
      setSuccessMsg(`Wallet credited by ${formatMoney(data.credited_amount)}.`);
      setErrorMsg(null);
      queryClient.invalidateQueries({ queryKey: ["payments", "balance"] });
      queryClient.invalidateQueries({ queryKey: ["payments", "history"] });
    },
    onError: (err: Error) => {
      setErrorMsg(err.message || "Unable to confirm payment intent.");
      setSuccessMsg(null);
    },
  });

  const loading = isLoadingMethods || isLoadingBalance || isLoadingHistory;

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

      {errorMsg ? <p className="mb-3 text-sm text-[var(--nq-accent-red)]">{errorMsg}</p> : null}
      {successMsg ? <p className="mb-3 text-sm text-[var(--nq-accent-green)]">{successMsg}</p> : null}

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
                className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-base)] px-2 py-1.5 text-sm text-[var(--nq-text-primary)] outline-none focus:border-[var(--nq-accent-cyan)]"
              />
            </label>

            <label className="flex flex-col gap-1 text-xs text-[var(--nq-text-secondary)]">
              Payment Method
              <select
                value={method}
                onChange={(event) => setMethod(event.target.value)}
                className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-base)] px-2 py-1.5 text-sm text-[var(--nq-text-primary)] outline-none focus:border-[var(--nq-accent-cyan)]"
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
              onClick={() => createIntentMutation.mutate()}
              disabled={createIntentMutation.isPending}
              className="rounded bg-[var(--nq-accent-cyan)] px-3 py-1.5 text-xs font-medium text-black disabled:opacity-60"
            >
              Create Payment Intent
            </button>

            <input
              type="text"
              value={otp}
              onChange={(event) => setOtp(event.target.value)}
              placeholder="Confirmation code"
              className="w-40 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-base)] px-2 py-1.5 text-xs text-[var(--nq-text-primary)] outline-none focus:border-[var(--nq-accent-cyan)]"
            />

            <button
              type="button"
              onClick={() => confirmIntentMutation.mutate()}
              disabled={!intent || confirmIntentMutation.isPending}
              className="rounded bg-[var(--nq-accent-green)] px-3 py-1.5 text-xs font-medium text-black disabled:opacity-60"
            >
              Confirm & Credit
            </button>
          </div>

          {intent ? (
            <div className="mt-4 rounded border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] px-3 py-2 text-xs text-[var(--nq-text-secondary)] font-mono">
              Intent: {intent.intent_id} | Provider Ref: {intent.provider_ref}
            </div>
          ) : null}
        </article>

        <article className="rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4 flex flex-col justify-center text-center">
          <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Wallet Balance</h2>
          <p className="text-3xl font-semibold text-[var(--nq-text-primary)] tracking-tight">
            {balanceData?.wallet_balance ? formatMoney(balanceData.wallet_balance) : "INR 0.00"}
          </p>
          <p className="mt-2 text-xs text-[var(--nq-text-secondary)]">Available cash for orders and rebalancing.</p>
        </article>
      </section>

      <section className="mt-6 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] p-4">
        <h2 className="mb-3 text-sm font-medium text-[var(--nq-text-secondary)]">Payment History</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-xs text-left">
            <thead>
              <tr className="text-[var(--nq-text-secondary)] border-b border-[var(--nq-border)]">
                <th className="pb-2 font-medium">Ref ID</th>
                <th className="pb-2 font-medium">Type</th>
                <th className="pb-2 text-right font-medium">Amount</th>
                <th className="pb-2 font-medium pl-4">Description</th>
                <th className="pb-2 font-medium">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--nq-border)]">
              {history.map((item: any) => (
                <tr key={item.id} className="hover:bg-[rgba(255,255,255,0.015)]">
                  <td className="py-2.5 font-mono">{item.id.slice(0, 8)}</td>
                  <td className="py-2.5 pl-4">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${item.type === 'credit' ? 'bg-[rgba(0,230,118,0.1)] text-[#00E676]' : 'bg-[rgba(255,59,92,0.1)] text-[#FF3B5C]'}`}>
                      {item.type}
                    </span>
                  </td>
                  <td className="py-2.5 text-right font-mono font-semibold">{formatMoney(item.amount)}</td>
                  <td className="py-2.5 font-semibold text-[var(--nq-text-secondary)] pl-4">{item.description}</td>
                  <td className="py-2.5 text-[var(--nq-text-secondary)] font-mono">{item.created_at ? new Date(item.created_at).toLocaleString() : "--"}</td>
                </tr>
              ))}
              {!loading && history.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-[var(--nq-text-secondary)]">
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
