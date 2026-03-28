"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { Moon, Sun } from "lucide-react";

import { contractsApi, type PortfolioHoldingsResponse } from "@/lib/contracts-api";
import { useUIStore } from "@/stores/ui-store";
import type { SignalResponse } from "@/types/intelligence";

interface TopBarProps {
  selectedSignal: SignalResponse | null;
  refreshing: boolean;
  signalStreamStatus: "connected" | "reconnecting" | "disconnected";
}

export default function TopBar({ selectedSignal, refreshing, signalStreamStatus }: TopBarProps): JSX.Element {
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
  const regimeColor = regime === "BULL" ? "bg-[rgba(0,230,118,0.15)] text-[#00E676]" : regime === "BEAR" ? "bg-[rgba(255,59,92,0.15)] text-[#FF3B5C]" : regime === "CRISIS" ? "bg-[rgba(220,38,38,0.20)] text-[#FF6B6B]" : "bg-[rgba(255,184,0,0.12)] text-[#FFB800]";
  const pnlColor = direction.includes("BUY") ? "text-[#00E676]" : direction.includes("SELL") ? "text-[#FF3B5C]" : "text-[#FFB800]";
  const navItems = [
    { href: "/markets", label: "Markets" },
    { href: "/research", label: "Research" },
    { href: "/backtest-lab", label: "Backtest" },
    { href: "/portfolio", label: "Portfolio" },
    { href: "/portfolio/orders", label: "Orders" },
    { href: "/screener", label: "Screener" },
    { href: "/alerts", label: "Alerts" },
  ];

  const { equityValue, unrealizedPnl } = useMemo(() => {
    const holdings = portfolio?.holdings ?? [];
    const equity = holdings.reduce((sum, item) => sum + item.quantity * item.ltp, 0);
    return {
      equityValue: equity,
      unrealizedPnl: portfolio?.total_unrealized_pnl ?? 0,
    };
  }, [portfolio]);

  return (
    <header className="col-span-1 border-b border-[var(--nq-border)] bg-[linear-gradient(90deg,rgba(10,16,26,0.98),rgba(10,13,20,0.92))] px-3 py-2 sm:px-4 lg:col-span-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 sm:gap-3">
          <span className="rounded bg-[rgba(0,212,255,0.12)] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--nq-accent-cyan)]">
            NQ
          </span>
          <span className="text-sm font-semibold tracking-wide text-[var(--nq-text-primary)] sm:text-base">Trading Terminal</span>
          <span className="hidden rounded border border-[var(--nq-border)] px-2 py-0.5 text-[10px] text-[var(--nq-text-secondary)] md:inline">
            {clock}
          </span>
          <span className={`rounded-full border border-[var(--nq-border-hover)] px-2 py-0.5 text-[10px] sm:text-xs ${regimeColor}`}>
            Regime {regime}
          </span>
        </div>

        <div className="flex items-center gap-2 text-[10px] sm:gap-3 sm:text-xs">
          <span className="hidden font-mono text-[var(--nq-text-secondary)] md:inline">
            Equity INR {equityValue.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
          </span>
          <span className={`rounded border border-current px-1.5 py-0.5 font-mono ${unrealizedPnl >= 0 ? "text-[#00E676]" : "text-[#FF3B5C]"}`}>
            Unrealized {unrealizedPnl >= 0 ? "+" : ""}{unrealizedPnl.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
          </span>
          <span className={`hidden rounded border border-current px-1.5 py-0.5 font-mono sm:inline ${pnlColor}`}>Signal {direction}</span>
        </div>
      </div>

      <div className="mt-2 flex items-center justify-between gap-2">
        <div className="hidden flex-1 items-center gap-2 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-1.5 lg:flex">
          <input
            ref={searchRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search symbols, research views, and macro events"
            className="w-full bg-transparent text-xs text-[var(--nq-text-primary)] outline-none placeholder:text-[var(--nq-text-secondary)]"
          />
          <span className="rounded border border-[var(--nq-border)] px-1.5 py-0.5 text-[10px] text-[var(--nq-text-secondary)]">Ctrl+K</span>
        </div>
        <div className="flex w-full items-center justify-between gap-2 lg:w-auto">
          <button
            type="button"
            onClick={toggleThemeMode}
            className="inline-flex items-center gap-1 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-2 py-1 text-[10px] text-[var(--nq-text-secondary)] transition hover:border-[var(--nq-border-hover)] sm:text-xs"
            title={themeMode === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            {themeMode === "dark" ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
            {themeMode === "dark" ? "Light" : "Dark"}
          </button>
          <span className="hidden items-center gap-1 rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-2 py-1 text-[10px] text-[var(--nq-text-secondary)] sm:inline-flex">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                signalStreamStatus === "connected"
                  ? "bg-[#00E676]"
                  : signalStreamStatus === "reconnecting"
                    ? "bg-[#FFB800] animate-pulse"
                    : "bg-[#FF3B5C]"
              }`}
            />
            {refreshing ? "Syncing" : `Signals ${signalStreamStatus}`}
          </span>
          <nav className="flex w-full items-center gap-1 overflow-x-auto pb-0.5 lg:w-auto lg:pb-0">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="whitespace-nowrap rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-2 py-1 text-[10px] text-[var(--nq-text-secondary)] transition hover:border-[var(--nq-border-hover)] hover:text-[var(--nq-text-primary)] sm:text-xs"
            >
              {item.label}
            </Link>
          ))}
          </nav>
        </div>
      </div>
    </header>
  );
}
