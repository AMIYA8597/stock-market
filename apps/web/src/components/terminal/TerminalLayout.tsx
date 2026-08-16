/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
"use client";

import { useState, useEffect, useRef, type ReactNode } from "react";
import { Panel, Group, Separator } from "react-resizable-panels";
import { cn } from "@/lib/utils";

interface TerminalLayoutProps {
  topBar: ReactNode;
  watchlist: ReactNode;
  chartSection: ReactNode;
  signalPanel: ReactNode;
  paperTradePanel?: ReactNode;
  alertsPanel?: ReactNode;
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
  paperTradePanel,
  alertsPanel,
  statusBanner,
  overlay,
  selectedSymbol,
  className,
}: TerminalLayoutProps): JSX.Element {
  const [activeTab, setActiveTab] = useState<"watchlist" | "chart" | "signal" | "orders">("watchlist");
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

  const [mounted, setMounted] = useState(false);
  const [isDesktop, setIsDesktop] = useState(true);
  
  useEffect(() => {
    setMounted(true);
    const media = window.matchMedia("(min-width: 1024px)");
    setIsDesktop(media.matches);
    const listener = () => setIsDesktop(media.matches);
    media.addEventListener("change", listener);
    return () => media.removeEventListener("change", listener);
  }, []);

  const [rightActiveTab, setRightActiveTab] = useState<"signal" | "orders" | "alerts">("signal");

  // Prevent hydration mismatch by rendering a structural skeleton until mounted
  if (!mounted) {
    return (
      <main className={cn("terminal-root relative", className)}>
         <div className={cn("terminal-grid nq-premium-bg nq-grid-overlay md:min-w-terminal", rowClass)}>
            <div className="terminal-topbar">{topBar}</div>
            <div className={cn("col-span-3 h-full min-h-0 w-full overflow-hidden flex items-center justify-center", contentRowClass)}>
               <div className="animate-pulse w-full h-full bg-[var(--bg-surface)]" />
            </div>
         </div>
      </main>
    );
  }

  return (
    <main className={cn("terminal-root relative", className)}>
      <div
        className={cn(
          "terminal-grid nq-premium-bg nq-grid-overlay md:min-w-terminal",
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
        <div className="col-span-3 flex border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 text-xs font-semibold uppercase tracking-wider lg:hidden shrink-0">
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
          <button
            onClick={() => setActiveTab("orders")}
            className={cn(
              "flex-1 py-3 text-center border-b-2 transition-all duration-200",
              activeTab === "orders"
                ? "border-[var(--accent-cyan)] text-[var(--text-primary)]"
                : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            )}
          >
            Orders
          </button>
        </div>

        {isDesktop ? (
          <div className={cn("col-span-3 h-full min-h-0 w-full overflow-hidden", contentRowClass)}>
            <Group orientation="horizontal">
              <Panel defaultSize={20} minSize={15} className="terminal-pane--left bg-[var(--bg-surface)] border-r border-[var(--border-subtle)]">
                {watchlist}
              </Panel>
              <Separator className="w-1.5 transition-colors hover:bg-[var(--accent-cyan)] data-[resize-handle-state=drag]:bg-[var(--accent-cyan)]" />
              <Panel defaultSize={55} minSize={30} className="terminal-pane--center bg-[var(--bg-base)] border-r border-[var(--border-subtle)]">
                {chartSection}
              </Panel>
              <Separator className="w-1.5 transition-colors hover:bg-[var(--accent-cyan)] data-[resize-handle-state=drag]:bg-[var(--accent-cyan)]" />
              <Panel defaultSize={25} minSize={20} className="terminal-pane--right bg-[var(--bg-surface)] flex flex-col h-full overflow-hidden">
                <div className="flex shrink-0 border-b border-[var(--border-subtle)] px-2 bg-[var(--bg-base)]">
                  <button onClick={() => setRightActiveTab("signal")} className={cn("px-3 py-2 text-[10px] font-semibold uppercase tracking-wider border-b-2 transition-all", rightActiveTab === "signal" ? "border-[var(--accent-cyan)] text-[var(--text-primary)]" : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]")}>AI Signal</button>
                  <button onClick={() => setRightActiveTab("orders")} className={cn("px-3 py-2 text-[10px] font-semibold uppercase tracking-wider border-b-2 transition-all", rightActiveTab === "orders" ? "border-[var(--accent-cyan)] text-[var(--text-primary)]" : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]")}>Orders / Paper</button>
                  <button onClick={() => setRightActiveTab("alerts")} className={cn("px-3 py-2 text-[10px] font-semibold uppercase tracking-wider border-b-2 transition-all", rightActiveTab === "alerts" ? "border-[var(--accent-cyan)] text-[var(--text-primary)]" : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]")}>Alerts</button>
                </div>
                <div className="flex-1 min-h-0 overflow-hidden">
                  <div className={cn("h-full w-full", rightActiveTab === "signal" ? "block" : "hidden")}>{signalPanel}</div>
                  <div className={cn("h-full w-full", rightActiveTab === "orders" ? "block" : "hidden")}>
                     {paperTradePanel}
                  </div>
                  <div className={cn("h-full w-full", rightActiveTab === "alerts" ? "block" : "hidden")}>
                     {alertsPanel}
                  </div>
                </div>
              </Panel>
            </Group>
          </div>
        ) : (
          <>
            <aside className={cn("terminal-pane terminal-pane--left h-full w-full", activeTab === "watchlist" ? "block" : "hidden", contentRowClass)}>
              {watchlist}
            </aside>
            <section className={cn("terminal-pane terminal-pane--center h-full w-full", activeTab === "chart" ? "block" : "hidden", contentRowClass)}>
              {chartSection}
            </section>
            <aside className={cn("terminal-pane terminal-pane--right h-full w-full", activeTab === "signal" ? "block" : "hidden", contentRowClass)}>
              {signalPanel}
            </aside>
            <aside className={cn("terminal-pane terminal-pane--orders h-full w-full", activeTab === "orders" ? "block" : "hidden", contentRowClass)}>
              {paperTradePanel}
            </aside>
          </>
        )}
      </div>

      {overlay ? (
        <div className="pointer-events-none absolute inset-0">
          {overlay}
        </div>
      ) : null}
    </main>
  );
}
