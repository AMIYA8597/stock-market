"use client";

import { DollarSign } from "lucide-react";
import Link from "next/link";

export default function ForexPage(): JSX.Element {
  return (
    <main className="min-h-screen bg-nq-bg-base flex flex-col items-center justify-center p-8 text-center">
      <div className="rounded-full bg-nq-bg-elevated p-6 mb-6">
        <DollarSign className="w-12 h-12 text-nq-accent" />
      </div>
      <h1 className="text-3xl font-bold text-nq-text-primary mb-2">Forex Markets</h1>
      <p className="text-nq-text-secondary max-w-md mb-8">
        Frankfurter/exchangerate.host integration is currently pending. Live forex rates and signals will be available in a future update.
      </p>
      <Link
        href="/markets/stocks"
        className="px-6 py-3 bg-nq-bg-card border border-nq-border rounded-lg text-nq-text-primary hover:text-nq-accent hover:border-nq-accent transition-colors"
      >
        View Stocks Universe
      </Link>
    </main>
  );
}
