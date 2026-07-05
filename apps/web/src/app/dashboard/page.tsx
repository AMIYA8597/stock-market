// src/app/dashboard/page.tsx
"use client";

import ChartSection from "@/components/terminal/ChartSection";
import DarkModeToggle from "@/components/ui/DarkModeToggle";

export default function DashboardPage() {
  const defaultSymbol = "NIFTY50";
  return (
    <div className="flex flex-col min-h-screen bg-[var(--nq-bg-primary)] text-[var(--nq-text-primary)]">
      <header className="flex items-center justify-between p-4 border-b border-[var(--nq-border)] bg-[var(--nq-bg-card)]">
        <h1 className="text-xl font-bold">Market Dashboard</h1>
        <DarkModeToggle />
      </header>
      <main className="flex-1 p-4 overflow-auto">
        <ChartSection defaultSymbol={defaultSymbol} />
      </main>
    </div>
  );
}
