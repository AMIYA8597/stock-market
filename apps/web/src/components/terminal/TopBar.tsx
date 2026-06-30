"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Moon, Search, Settings2, Sun } from "lucide-react";

import { contractsApi, type PortfolioHoldingsResponse, type MarketIndex } from "@/lib/contracts-api";
import { systemApi } from "@/lib/api-client";
import { useUIStore } from "@/stores/ui-store";
import type { SignalResponse } from "@/types/intelligence";
import { useTradingStore } from "@/stores/tradingStore";

import { usePriceFeed } from "@/hooks/usePriceFeed";

interface TopBarProps {
  selectedSignal: SignalResponse | null;
  refreshing: boolean;
  signalStreamStatus: "connected" | "reconnecting" | "disconnected";
}

function getNSEMarketStatus(): { status: "OPEN" | "CLOSED"; countdown: string } {
  const options = { timeZone: "Asia/Kolkata" };
  let istString: string;
  try {
    istString = new Date().toLocaleString("en-US", options);
  } catch (e) {
    istString = new Date().toLocaleString();
  }
  const istDate = new Date(istString);
  const day = istDate.getDay(); // 0 = Sunday, 6 = Saturday
  const hours = istDate.getHours();
  const minutes = istDate.getMinutes();
  const totalMinutes = hours * 60 + minutes;

  const isOpenDay = day >= 1 && day <= 5; // Monday to Friday
  const isOpenTime = totalMinutes >= 555 && totalMinutes < 930;
  const isMarketOpen = isOpenDay && isOpenTime;

  if (isMarketOpen) {
    return { status: "OPEN", countdown: "" };
  }

  const nextOpen = new Date(istDate);
  if (!isOpenDay) {
    const daysToAdd = day === 6 ? 2 : 1;
    nextOpen.setDate(istDate.getDate() + daysToAdd);
    nextOpen.setHours(9, 15, 0, 0);
  } else if (totalMinutes >= 930) {
    const daysToAdd = day === 5 ? 3 : 1;
    nextOpen.setDate(istDate.getDate() + daysToAdd);
    nextOpen.setHours(9, 15, 0, 0);
  } else if (totalMinutes < 555) {
    nextOpen.setHours(9, 15, 0, 0);
  }

  const diffMs = nextOpen.getTime() - istDate.getTime();
  if (diffMs <= 0) {
    return { status: "OPEN", countdown: "" };
  }

  const diffHrs = Math.floor(diffMs / (3600 * 1000));
  const diffMins = Math.floor((diffMs % (3600 * 1000)) / (60 * 1000));
  const diffSecs = Math.floor((diffMs % (60 * 1000)) / 1000);

  const pad = (n: number) => String(n).padStart(2, "0");
  return {
    status: "CLOSED",
    countdown: `${pad(diffHrs)}h ${pad(diffMins)}m ${pad(diffSecs)}s`,
  };
}

export default function TopBar({
  selectedSignal,
  refreshing,
  signalStreamStatus,
}: TopBarProps): JSX.Element {
  const { tradingMode, connectionStatus, triggerKillSwitch, fetchStatus } = useTradingStore();
  const { status: priceFeedStatus } = usePriceFeed(["^NSEI"]);
  const [portfolio, setPortfolio] = useState<PortfolioHoldingsResponse | null>(null);
  const [indices, setIndices] = useState<MarketIndex[]>([]);
  const [healthStatus, setHealthStatus] = useState<Record<string, "up" | "down">>({
    yfinance: "down",
    nse: "down",
    coingecko: "down",
    fred: "down",
  });
  const [marketStatus, setMarketStatus] = useState<{ status: "OPEN" | "CLOSED"; countdown: string }>({
    status: "CLOSED",
    countdown: "",
  });

  useEffect(() => {
    void fetchStatus();
    const interval = setInterval(() => {
      void fetchStatus();
    }, 10000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  useEffect(() => {
    let active = true;

    async function checkHealth() {
      try {
        const res = await systemApi.getLiveDataHealth();
        if (active) setHealthStatus(res);
      } catch (err) {
        console.error("Health check failed", err);
      }
    }

    async function loadIndices() {
      try {
        const res = await contractsApi.getIndices();
        if (active) setIndices(res);
      } catch (err) {
        console.error("Failed to load indices", err);
      }
    }

    void checkHealth();
    void loadIndices();

    const healthInterval = setInterval(checkHealth, 30000);
    const indicesInterval = setInterval(loadIndices, 10000);

    return () => {
      active = false;
      clearInterval(healthInterval);
      clearInterval(indicesInterval);
    };
  }, []);

  useEffect(() => {
    setMarketStatus(getNSEMarketStatus());
    const timer = setInterval(() => {
      setMarketStatus(getNSEMarketStatus());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const [clock, setClock] = useState<string>("");
  const [query, setQuery] = useState<string>("");
  const [mounted, setMounted] = useState<boolean>(false);
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
    setMounted(true);
    setClock(new Date().toLocaleTimeString());
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

  const confidence = selectedSignal ? Number(selectedSignal.ensemble.confidence) * 100 : null;
  const directionText = confidence !== null ? `${direction.replace("_", " ")} ${Math.round(confidence)}%` : direction.replace("_", " ");

  const badgeStyle = 
    direction === "STRONG_BUY"
      ? "bg-[rgba(0,230,118,0.18)] text-[#00E676] border-[#00E676]"
      : direction === "BUY"
        ? "bg-[rgba(0,230,118,0.10)] text-[#00E676] border-[#00E676]"
        : direction === "STRONG_SELL"
          ? "bg-[rgba(255,59,92,0.18)] text-[#FF3B5C] border-[#FF3B5C]"
          : direction === "SELL"
            ? "bg-[rgba(255,59,92,0.10)] text-[#FF3B5C] border-[#FF3B5C]"
            : "bg-[rgba(150,150,150,0.10)] text-[#9E9E9E] border-[#9E9E9E]";

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
      <div className="flex min-w-[220px] items-center gap-2 terminal:min-w-[280px]">
        <span className="rounded bg-[rgba(0,212,245,0.16)] px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--accent-cyan)] shrink-0">
          NQ
        </span>
        <span className="font-display text-sm font-semibold tracking-[0.01em] text-[var(--text-primary)] shrink-0">
          NeuroQuant
        </span>
        <span className={`hidden rounded-full px-2 py-0.5 text-[10px] font-medium terminal:inline-flex ${regimeClassName} shrink-0`}>
          {regime}
        </span>

        {/* NSE Market Status */}
        <div className="flex flex-col ml-1.5 border-l border-[var(--border-subtle)] pl-2 shrink-0">
          <div className="flex items-center gap-1.5">
            <span className={`h-1.5 w-1.5 rounded-full ${marketStatus.status === "OPEN" ? "bg-[var(--accent-green)]" : "bg-[var(--accent-red)]"}`} />
            <span className="text-[9px] font-bold uppercase tracking-wider text-[var(--text-secondary)]">NSE {marketStatus.status}</span>
          </div>
          {marketStatus.status === "CLOSED" && marketStatus.countdown && (
            <span className="text-[8px] font-mono text-[var(--text-secondary)] opacity-85" title="Countdown to next open">
              {marketStatus.countdown}
            </span>
          )}
        </div>
      </div>

      {/* Center Section: Indices Ticker + Search */}
      <div className="hidden min-w-0 flex-1 items-center justify-between gap-4 px-2 terminal:flex">
        {/* Index Ticker Strip */}
        <div className="flex items-center gap-3 overflow-x-auto ds-scrollable pr-2 max-w-[60%] lg:max-w-[70%]">
          {indices.map((idx) => {
            const isUp = idx.change >= 0;
            return (
              <div
                key={idx.ticker}
                className="flex items-center gap-1.5 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 font-mono text-[10px] shrink-0"
              >
                <span className="font-bold text-[var(--text-secondary)]">{idx.name}</span>
                <span className="text-[var(--text-primary)]">{idx.value.toLocaleString("en-IN", { minimumFractionDigits: 1 })}</span>
                <span className={isUp ? "text-[var(--accent-green)]" : "text-[var(--accent-red)]"}>
                  {isUp ? "+" : ""}{Number(idx.change_pct ?? 0).toFixed(2)}%
                </span>
              </div>
            );
          })}
          {indices.length === 0 && (
            <div className="text-[10px] text-[var(--text-secondary)] font-mono animate-pulse">Loading index feed...</div>
          )}
        </div>

        {/* Search Input */}
        <div className="flex flex-1 max-w-[200px] items-center gap-2 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 shrink-0">
          <Search className="h-3 w-3 text-[var(--text-secondary)]" />
          <input
            ref={searchRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search..."
            className="w-full bg-transparent text-[10px] text-[var(--text-primary)] outline-none placeholder:text-[var(--text-secondary)]"
          />
          <span className="rounded border border-[var(--border-subtle)] px-1 py-0.5 font-mono text-[8px] text-[var(--text-secondary)]">
            Ctrl+K
          </span>
        </div>
      </div>

      <div className="ml-auto flex min-w-[220px] items-center justify-end gap-2 terminal:min-w-[300px] shrink-0">
        <div className="hidden text-right terminal:block">
          <div className="font-mono text-[11px] text-[var(--text-primary)]">
            ₹{equityValue.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
          </div>
          <div className={`font-mono text-[10px] ${unrealizedPnl >= 0 ? "text-[var(--accent-green)]" : "text-[var(--accent-red)]"}`}>
            {unrealizedPnl >= 0 ? "+" : ""}
            {unrealizedPnl.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
          </div>
        </div>

        {/* Feeds Health Indicators */}
        <div className="hidden items-center gap-2 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-[9px] text-[var(--text-secondary)] xl:inline-flex">
          <span className="text-[7px] uppercase tracking-wider font-semibold text-[var(--text-secondary)] mr-1">Feeds:</span>
          {Object.entries(healthStatus).map(([source, status]) => (
            <div
              key={source}
              className="flex items-center gap-1 cursor-default"
              title={`${source.toUpperCase()}: ${status === "up" ? "Connected" : "Disconnected"}`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${status === "up" ? "bg-[var(--accent-green)]" : "bg-[var(--accent-red)]"}`} />
              <span className="text-[8px] uppercase tracking-wider opacity-85">{source}</span>
            </div>
          ))}
        </div>

        <span className="hidden items-center gap-1 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-[10px] text-[var(--text-secondary)] terminal:inline-flex">
          <span className={`h-1.5 w-1.5 rounded-full ${streamClassName}`} />
          {refreshing ? "Syncing" : signalStreamStatus}
        </span>

        <span className="hidden items-center gap-1 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-[10px] text-[var(--text-secondary)] terminal:inline-flex" title="Live Price Feed WebSocket Connection State">
          <span className={`h-1.5 w-1.5 rounded-full ${
            priceFeedStatus === "connected"
              ? "bg-[var(--accent-green)]"
              : priceFeedStatus === "reconnecting"
                ? "bg-[var(--accent-amber)] animate-pulse"
                : "bg-[var(--accent-red)]"
          }`} />
          Price Feed: {priceFeedStatus}
        </span>

        <span className="hidden items-center gap-1 rounded border border-[var(--border-subtle)] bg-[var(--bg-elevated)] px-2 py-1 text-[10px] text-[var(--text-secondary)] terminal:inline-flex" title="Upstox WebSocket Connection State">
          <span className={`h-1.5 w-1.5 rounded-full ${
            connectionStatus === "connected"
              ? "bg-[var(--accent-green)]"
              : connectionStatus === "reconnecting" || connectionStatus === "connecting"
                ? "bg-[var(--accent-amber)] animate-pulse"
                : "bg-[var(--accent-red)]"
          }`} />
          Upstox: {connectionStatus}
        </span>

        <span className={`hidden rounded border px-2 py-1 font-mono text-[10px] terminal:inline-flex items-center gap-1.5 font-bold uppercase tracking-wider ${badgeStyle}`}>
          {direction === "STRONG_BUY" && (
            <span className="h-1.5 w-1.5 rounded-full bg-[#00E676] animate-pulse" />
          )}
          {direction === "STRONG_SELL" && (
            <span className="h-1.5 w-1.5 rounded-full bg-[#FF3B5C] animate-pulse" />
          )}
          {direction === "BUY" && (
            <span className="h-1.5 w-1.5 rounded-full bg-[#00E676]" />
          )}
          {direction === "SELL" && (
            <span className="h-1.5 w-1.5 rounded-full bg-[#FF3B5C]" />
          )}
          {direction === "NEUTRAL" && (
            <span className="h-1.5 w-1.5 rounded-full bg-[#9E9E9E]" />
          )}
          {directionText}
        </span>

        <button
          type="button"
          onClick={async () => {
            await triggerKillSwitch();
            alert("EMERGENCY KILL SWITCH: Trading mode forced to PAPER. All pending simulation orders cancelled.");
          }}
          className={`inline-flex items-center gap-1 rounded border px-2 py-1 text-[10px] font-bold uppercase tracking-wider transition ${
            tradingMode === "LIVE"
              ? "border-[#FF3B5C] bg-[rgba(255,59,92,0.18)] text-[#FF3B5C] animate-pulse"
              : "border-[var(--border-subtle)] bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:border-[var(--border-muted)]"
          }`}
          title="Emergency Kill Switch: immediately reverts to PAPER and cancels simulation orders"
        >
          🚨 Kill Switch ({tradingMode})
        </button>

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
          {mounted ? clock : "--:--:--"}
        </span>
      </div>
    </header>
  );
}