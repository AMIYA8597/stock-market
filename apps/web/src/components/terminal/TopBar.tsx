"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Moon, Search, Settings2, Sun } from "lucide-react";

import { contractsApi, type PortfolioHoldingsResponse } from "@/lib/contracts-api";
import { useUIStore } from "@/stores/ui-store";
import type { SignalResponse } from "@/types/intelligence";

interface TopBarProps {
  selectedSignal: SignalResponse | null;
  refreshing: boolean;
  signalStreamStatus: "connected" | "reconnecting" | "disconnected";
}

export default function TopBar({
  selectedSignal,
  refreshing,
  signalStreamStatus,
}: TopBarProps): JSX.Element {
  const [portfolio, setPortfolio] = useState<PortfolioHoldingsResponse | null>(null);
  const [clock, setClock] = useState<string>(new Date().toLocaleTimeString());
  const [query, setQuery] = useState<string>("");
  const searchRef = useRef<HTMLInputElement | null>(null);
  const themeMode = useUIStore((state) => state.themeMode);
  const toggleThemeMode = useUIStore((state) => state.toggleThemeMode);

  useEffect(() => {
    let mounted = true;

    async function loadPortfolio(): Promise<void> {
      try {
        const data = await contractsApi.getPortfolioHoldings();
        if (mounted) {
          setPortfolio(data);
        }
      } catch {
        if (mounted) {
          setPortfolio(null);
        }
      }
    }

    void loadPortfolio();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      setClock(new Date().toLocaleTimeString());
    }, 1000);

    return () => {
      clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent): void => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchRef.current?.focus();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  const regime = selectedSignal?.regime.state ?? "SIDEWAYS";
  const direction = selectedSignal?.ensemble.direction ?? "NEUTRAL";

  const regimeClassName =
    regime === "BULL"
      ? "bg-[var(--regime-bull)] text-[var(--accent-green)]"
      : regime === "BEAR"
        ? "bg-[var(--regime-bear)] text-[var(--accent-red)]"
        : regime === "CRISIS"
          ? "bg-[var(--regime-crisis)] text-[var(--accent-red)]"
          : "bg-[var(--regime-side)] text-[var(--accent-amber)]";

  const streamClassName =
    signalStreamStatus === "connected"
      ? "bg-[var(--accent-green)]"
      : signalStreamStatus === "reconnecting"
        ? "bg-[var(--accent-amber)] animate-pulse"
        : "bg-[var(--accent-red)]";

  const pnlColorClassName = direction.includes("BUY")
    ? "text-[var(--accent-green)]"
    : direction.includes("SELL")
      ? "text-[var(--accent-red)]"
      : "text-[var(--accent-amber)]";

  const { equityValue, unrealizedPnl } = useMemo(() => {
    const holdings = portfolio?.holdings ?? [];
    const equity = holdings.reduce((sum, item) => sum + item.quantity * item.ltp, 0);
    return {
      equityValue: equity,
      unrealizedPnl: portfolio?.total_unrealized_pnl ?? 0,
    };
  }, [portfolio]);

  return (
    <header className="flex h-[var(--terminal-topbar-height)] items-center gap-2 px-3 text-xs terminal:px-4">
      <div className="flex min-w-[220px] items-center gap-2 terminal:min-w-[260px]">
        <span className="rounded bg-[rgba(0,212,245,0.16)] px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--accent-cyan)]">
          NQ
        </span>
        <span className="font-display text-sm font-semibold tracking-[0.01em] text-[var(--text-primary)]">
          NeuroQuant Terminal
        </span>
        <span className={`hidden rounded-full px-2 py-0.5 text-[10px] font-medium terminal:inline-flex ${regimeClassName}`}>
          {regime}
        </span>
      </div>

      <div className="hidden min-w-0 flex-1 items-center gap-2 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2.5 py-1 terminal:flex">
        <Search className="h-3.5 w-3.5 text-[var(--text-secondary)]" />
        <input
          ref={searchRef}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search symbols, research, macro events"
          className="w-full bg-transparent text-xs text-[var(--text-primary)] outline-none placeholder:text-[var(--text-secondary)]"
        />
        <span className="rounded border border-[var(--border-subtle)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--text-secondary)]">
          Ctrl+K
        </span>
      </div>

      <div className="ml-auto flex min-w-[220px] items-center justify-end gap-2 terminal:min-w-[300px]">
        <div className="hidden text-right terminal:block">
          <div className="font-mono text-[11px] text-[var(--text-primary)]">
            ₹{equityValue.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
          </div>
          <div className={`font-mono text-[10px] ${unrealizedPnl >= 0 ? "text-[var(--accent-green)]" : "text-[var(--accent-red)]"}`}>
            {unrealizedPnl >= 0 ? "+" : ""}
            {unrealizedPnl.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
          </div>
        </div>

        <span className="hidden items-center gap-1 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-[10px] text-[var(--text-secondary)] terminal:inline-flex">
          <span className={`h-1.5 w-1.5 rounded-full ${streamClassName}`} />
          {refreshing ? "Syncing" : signalStreamStatus}
        </span>

        <span className={`hidden rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 font-mono text-[10px] terminal:inline-flex ${pnlColorClassName}`}>
          {direction}
        </span>

        <button
          type="button"
          onClick={toggleThemeMode}
          className="inline-flex items-center gap-1 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-[10px] text-[var(--text-secondary)] transition hover:border-[var(--border-muted)]"
          title={themeMode === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {themeMode === "dark" ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
          {themeMode === "dark" ? "Light" : "Dark"}
        </button>

        <button
          type="button"
          className="inline-flex items-center justify-center rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] p-1.5 text-[var(--text-secondary)] transition hover:border-[var(--border-muted)] hover:text-[var(--text-primary)]"
          aria-label="Terminal settings"
        >
          <Settings2 className="h-3.5 w-3.5" />
        </button>

        <span className="hidden rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 font-mono text-[10px] text-[var(--text-secondary)] xl:inline-flex">
          {clock}
        </span>
      </div>
    </header>
  );
}