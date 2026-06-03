"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { AmbientLucideBackground } from "@/components/common/ambient-lucide-background";

const tabs = [
  { href: "/research/regime-analysis", label: "Regime" },
  { href: "/research/correlation-graph", label: "Correlation" },
  { href: "/research/factor-exposure", label: "Factor Exposure" },
  { href: "/research/model-performance", label: "Model Performance" },
  { href: "/research/explainability/RELIANCE.NS", label: "Explainability" },
];

export default function ResearchLayout({ children }: { children: ReactNode }): JSX.Element {
  const pathname = usePathname();

  return (
    <main className="relative min-h-screen bg-[var(--nq-bg-base)] text-[var(--nq-text-primary)]">
      <AmbientLucideBackground className="opacity-90" />
      <header className="relative z-10 border-b border-[var(--nq-border)] bg-[var(--nq-bg-card)]/60 px-4 py-4 backdrop-blur sm:px-6">
        <h1 className="text-lg font-semibold tracking-tight">Research Workbench</h1>
        <nav className="mt-3 flex flex-wrap gap-2">
          {tabs.map((tab) => (
            <Link
              key={tab.href}
              href={tab.href}
              className={`rounded border px-3 py-1 text-xs transition ${
                pathname === tab.href
                  ? "border-[var(--nq-accent-cyan)] bg-[rgba(0,212,245,0.14)] text-[var(--nq-accent-cyan)]"
                  : "border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] text-[var(--nq-text-secondary)] hover:border-[var(--nq-accent-cyan)] hover:text-[var(--nq-accent-cyan)]"
              }`}
            >
              {tab.label}
            </Link>
          ))}
        </nav>
      </header>
      <section className="relative z-10 p-4 sm:p-6">{children}</section>
    </main>
  );
}
