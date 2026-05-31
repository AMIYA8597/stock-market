"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface TerminalLayoutProps {
  topBar: ReactNode;
  watchlist: ReactNode;
  chartSection: ReactNode;
  signalPanel: ReactNode;
  statusBanner?: ReactNode;
  overlay?: ReactNode;
  className?: string;
}

export default function TerminalLayout({
  topBar,
  watchlist,
  chartSection,
  signalPanel,
  statusBanner,
  overlay,
  className,
}: TerminalLayoutProps): JSX.Element {
  const withBanner = Boolean(statusBanner);
  const rowClass = withBanner ? "grid-rows-terminal-with-banner" : "grid-rows-terminal";
  const contentRowClass = withBanner ? "row-start-3" : "row-start-2";

  return (
    <main className={cn("terminal-root relative overflow-x-auto", className)}>
      <div
        className={cn(
          "terminal-grid nq-premium-bg nq-grid-overlay min-w-terminal",
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

        <aside className={cn("terminal-pane terminal-pane--left", contentRowClass)}>
          {watchlist}
        </aside>

        <section className={cn("terminal-pane terminal-pane--center", contentRowClass)}>
          {chartSection}
        </section>

        <aside className={cn("terminal-pane terminal-pane--right", contentRowClass)}>
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