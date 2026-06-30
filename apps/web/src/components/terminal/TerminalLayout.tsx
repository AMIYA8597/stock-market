"use client";

import { useState, useEffect, useRef, type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface TerminalLayoutProps {
  topBar: ReactNode;
  watchlist: ReactNode;
  chartSection: ReactNode;
  signalPanel: ReactNode;
  statusBanner?: ReactNode;
  overlay?: ReactNode;
  selectedSymbol?: string;
  className?: string;
}

export default function TerminalLayout({
  topBar,
  watchlist,
  chartSection,
  signalPanel,
  statusBanner,
  overlay,
  selectedSymbol,
  className,
}: TerminalLayoutProps): JSX.Element {
  const [activeTab, setActiveTab] = useState<"watchlist" | "chart" | "signal">("watchlist");
  const withBanner = Boolean(statusBanner);
  const rowClass = withBanner ? "grid-rows-terminal-with-banner" : "grid-rows-terminal";
  const contentRowClass = withBanner ? "row-start-3" : "row-start-2";

  // Watch for symbol selection from watchlist to auto-switch tab to chart on mobile/tablet
  const lastSymbolRef = useRef(selectedSymbol);
  useEffect(() => {
    if (selectedSymbol && selectedSymbol !== lastSymbolRef.current) {
      setActiveTab("chart");
      lastSymbolRef.current = selectedSymbol;
    }
  }, [selectedSymbol]);

  return (
    <main className={cn("terminal-root relative", className)}>
      <div
        className={cn(
          "terminal-grid nq-premium-bg nq-grid-overlay terminal:min-w-terminal",
          rowClass,
        )}
      >
        <div className="terminal-topbar">
          {topBar}
        </div>

        {withBanner ? (
          <div className="col-span-3 row-start-2 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-layout-gutter py-2 text-xs text-[var(--text-secondary)]">
            {statusBanner}
          </div>
        ) : null}

        {/* Premium Glassmorphic Tab Bar for Mobile & Tablet viewports */}
        <div className="col-span-3 flex border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 text-xs font-semibold uppercase tracking-wider terminal:hidden shrink-0">
          <button
            onClick={() => setActiveTab("watchlist")}
            className={cn(
              "flex-1 py-3 text-center border-b-2 transition-all duration-200",
              activeTab === "watchlist"
                ? "border-[var(--accent-cyan)] text-[var(--text-primary)]"
                : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            )}
          >
            Watchlist
          </button>
          <button
            onClick={() => setActiveTab("chart")}
            className={cn(
              "flex-1 py-3 text-center border-b-2 transition-all duration-200",
              activeTab === "chart"
                ? "border-[var(--accent-cyan)] text-[var(--text-primary)]"
                : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            )}
          >
            Live Chart
          </button>
          <button
            onClick={() => setActiveTab("signal")}
            className={cn(
              "flex-1 py-3 text-center border-b-2 transition-all duration-200",
              activeTab === "signal"
                ? "border-[var(--accent-cyan)] text-[var(--text-primary)]"
                : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            )}
          >
            AI Trade
          </button>
        </div>

        <aside className={cn(
          "terminal-pane terminal-pane--left", 
          activeTab === "watchlist" ? "block" : "hidden", 
          "terminal:block", 
          contentRowClass
        )}>
          {watchlist}
        </aside>

        <section className={cn(
          "terminal-pane terminal-pane--center", 
          activeTab === "chart" ? "block" : "hidden", 
          "terminal:block", 
          contentRowClass
        )}>
          {chartSection}
        </section>

        <aside className={cn(
          "terminal-pane terminal-pane--right", 
          activeTab === "signal" ? "block" : "hidden", 
          "terminal:block", 
          contentRowClass
        )}>
          {signalPanel}
        </aside>
      </div>

      {overlay ? (
        <div className="pointer-events-none absolute inset-0">
          {overlay}
        </div>
      ) : null}
    </main>
  );
}
