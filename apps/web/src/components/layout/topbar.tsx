"use client";

import { Search, Bell, Wifi, WifiOff, Command, Menu, Moon, Sun } from "lucide-react";
import { useUIStore } from "@/stores/ui-store";

interface TopbarProps {
  connectionStatus: "connected" | "reconnecting" | "disconnected";
  alertCount?: number;
}

export function Topbar({ connectionStatus, alertCount = 0 }: TopbarProps) {
  const { openCommandPalette, toggleMobileSidebar, themeMode, toggleThemeMode } = useUIStore();

  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-[rgba(7,9,15,0.76)] px-4 py-3 backdrop-blur-2xl sm:px-6">
      <div className="mx-auto flex max-w-[1680px] items-center justify-between gap-3">
      {/* Search */}
      <div className="flex items-center gap-2">
        <button
          onClick={toggleMobileSidebar}
          className="flex h-10 w-10 items-center justify-center rounded-[1rem] border border-white/10 bg-white/5 text-[var(--nq-text-secondary)] transition hover:bg-white/[0.08] hover:text-[var(--nq-text-primary)] lg:hidden"
          aria-label="Open menu"
        >
          <Menu className="h-4 w-4" />
        </button>

        <button
          onClick={openCommandPalette}
          className="hidden w-[min(34vw,360px)] items-center gap-2 rounded-[1rem] border border-white/10 bg-white/5 px-3.5 py-2 text-sm text-[var(--nq-text-secondary)] transition-all hover:border-white/15 hover:bg-white/[0.08] hover:text-[var(--nq-text-primary)] sm:flex"
        >
          <Search className="h-4 w-4" />
          <span className="flex-1 text-left">Search stocks, crypto, pages...</span>
          <kbd className="flex items-center gap-0.5 rounded-lg border border-white/10 bg-white/[0.08] px-1.5 py-0.5 text-[10px] font-mono text-[var(--nq-text-secondary)]">
            <Command className="h-2.5 w-2.5" />K
          </kbd>
        </button>

        <button
          onClick={openCommandPalette}
          className="flex h-10 w-10 items-center justify-center rounded-[1rem] border border-white/10 bg-white/5 text-[var(--nq-text-secondary)] transition hover:bg-white/[0.08] hover:text-[var(--nq-text-primary)] sm:hidden"
          aria-label="Open search"
        >
          <Search className="h-4 w-4" />
        </button>
      </div>

      {/* Right section */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Connection status */}
        <div className="hidden items-center gap-1.5 sm:flex">
          {connectionStatus === "connected" ? (
            <Wifi className="h-3.5 w-3.5 text-[var(--nq-bull)]" />
          ) : connectionStatus === "reconnecting" ? (
            <Wifi className="h-3.5 w-3.5 animate-pulse text-[var(--nq-warning)]" />
          ) : (
            <WifiOff className="h-3.5 w-3.5 text-[var(--nq-bear)]" />
          )}
          <span className="text-[10px] uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">
            {connectionStatus === "connected" ? "Live" : connectionStatus === "reconnecting" ? "Reconnecting" : "Offline"}
          </span>
        </div>

        {/* Notifications */}
        <button
          onClick={toggleThemeMode}
          className="flex h-10 w-10 items-center justify-center rounded-[1rem] border border-white/10 bg-white/5 transition hover:bg-white/[0.08]"
          aria-label="Toggle theme"
          title={themeMode === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {themeMode === "dark" ? (
            <Sun className="h-4.5 w-4.5 text-[var(--nq-text-secondary)]" />
          ) : (
            <Moon className="h-4.5 w-4.5 text-[var(--nq-text-secondary)]" />
          )}
        </button>

        <button className="relative flex h-10 w-10 items-center justify-center rounded-[1rem] border border-white/10 bg-white/5 transition hover:bg-white/[0.08]">
          <Bell className="h-4.5 w-4.5 text-[var(--nq-text-secondary)]" />
          {alertCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-[var(--nq-bear)] text-[9px] font-bold text-white">
              {alertCount > 9 ? "9+" : alertCount}
            </span>
          )}
        </button>

        {/* Profile */}
        <button className="flex h-9 w-9 items-center justify-center rounded-full bg-[linear-gradient(135deg,var(--nq-accent),#65f7d2)] text-sm font-bold text-black shadow-[0_12px_24px_rgba(0,212,245,0.18)]">
          NQ
        </button>
      </div>
      </div>
    </header>
  );
}
