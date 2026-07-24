"use client";

import { PricingPage, CheckoutPage, TransactionsPage } from "@/modules/payments/PaymentPages";
import { AuthGuard } from "@/components/auth/AuthGuard";
import { Wallet, CreditCard, Receipt } from "lucide-react";
import { useState } from "react";

export default function BillingDashboard() {
  const [activeTab, setActiveTab] = useState<"pricing" | "topup" | "ledger">("pricing");

  return (
    <AuthGuard>
      <div className="flex h-full min-h-screen flex-col bg-[var(--nq-bg-base)]">
        {/* Header */}
        <header className="flex h-14 items-center justify-between border-b border-[var(--nq-border)] bg-[var(--nq-bg-surface)] px-6">
          <h1 className="text-lg font-bold text-[var(--nq-text-primary)]">Billing & Payments</h1>
        </header>

        {/* Navigation Tabs */}
        <div className="flex border-b border-[var(--nq-border)] bg-[var(--nq-bg-surface)] px-6 pt-4 gap-6">
          <button
            onClick={() => setActiveTab("pricing")}
            className={`flex items-center gap-2 pb-3 font-semibold transition-colors border-b-2 ${
              activeTab === "pricing"
                ? "border-[var(--nq-accent-cyan)] text-[var(--nq-text-primary)]"
                : "border-transparent text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)]"
            }`}
          >
            <CreditCard className="w-4 h-4" /> Subscription Plans
          </button>
          <button
            onClick={() => setActiveTab("topup")}
            className={`flex items-center gap-2 pb-3 font-semibold transition-colors border-b-2 ${
              activeTab === "topup"
                ? "border-[var(--nq-accent-cyan)] text-[var(--nq-text-primary)]"
                : "border-transparent text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)]"
            }`}
          >
            <Wallet className="w-4 h-4" /> Wallet Top-Up
          </button>
          <button
            onClick={() => setActiveTab("ledger")}
            className={`flex items-center gap-2 pb-3 font-semibold transition-colors border-b-2 ${
              activeTab === "ledger"
                ? "border-[var(--nq-accent-cyan)] text-[var(--nq-text-primary)]"
                : "border-transparent text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)]"
            }`}
          >
            <Receipt className="w-4 h-4" /> Ledger & Transactions
          </button>
        </div>

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto p-6 md:p-10">
          <div className="mx-auto max-w-6xl">
            {activeTab === "pricing" && <PricingPage />}
            {activeTab === "topup" && (
              <div className="flex justify-center mt-10">
                <CheckoutPage />
              </div>
            )}
            {activeTab === "ledger" && <TransactionsPage />}
          </div>
        </main>
      </div>
    </AuthGuard>
  );
}
