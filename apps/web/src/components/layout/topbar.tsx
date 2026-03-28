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
    <header
      className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-nq-border bg-nq-bg-secondary/80 backdrop-blur-md px-6"
    >
      {/* Search */}
      <div className="flex items-center gap-2">
        <button
          onClick={toggleMobileSidebar}
          className="flex h-9 w-9 items-center justify-center rounded-nq border border-nq-border bg-nq-bg-card text-nq-text-secondary transition-colors hover:border-nq-border-hover hover:text-nq-text-primary lg:hidden"
          aria-label="Open menu"
        >
          <Menu className="h-4 w-4" />
        </button>

        <button
          onClick={openCommandPalette}
          className="hidden w-72 items-center gap-2 rounded-nq border border-nq-border bg-nq-bg-card px-3 py-1.5 text-sm text-nq-text-tertiary transition-all hover:border-nq-border-hover hover:text-nq-text-secondary sm:flex"
        >
          <Search className="h-4 w-4" />
          <span className="flex-1 text-left">Search stocks, crypto, pages...</span>
          <kbd className="flex items-center gap-0.5 rounded border border-nq-border bg-nq-bg-elevated px-1.5 py-0.5 text-[10px] font-mono text-nq-text-tertiary">
            <Command className="h-2.5 w-2.5" />K
          </kbd>
        </button>

        <button
          onClick={openCommandPalette}
          className="flex h-9 w-9 items-center justify-center rounded-nq border border-nq-border bg-nq-bg-card text-nq-text-secondary transition-colors hover:border-nq-border-hover hover:text-nq-text-primary sm:hidden"
          aria-label="Open search"
        >
          <Search className="h-4 w-4" />
        </button>
      </div>

      {/* Right section */}
      <div className="flex items-center gap-3">
        {/* Connection status */}
        <div className="hidden items-center gap-1.5 sm:flex">
          {connectionStatus === "connected" ? (
            <Wifi className="h-3.5 w-3.5 text-nq-bull" />
          ) : connectionStatus === "reconnecting" ? (
            <Wifi className="h-3.5 w-3.5 text-nq-warning animate-pulse" />
          ) : (
            <WifiOff className="h-3.5 w-3.5 text-nq-bear" />
          )}
          <span className="text-[10px] text-nq-text-tertiary uppercase tracking-wider">
            {connectionStatus === "connected" ? "Live" : connectionStatus === "reconnecting" ? "Reconnecting" : "Offline"}
          </span>
        </div>

        {/* Notifications */}
        <button
          onClick={toggleThemeMode}
          className="flex h-9 w-9 items-center justify-center rounded-nq hover:bg-nq-bg-card transition-colors"
          aria-label="Toggle theme"
          title={themeMode === "dark" ? "Switch to light mode" : "Switch to dark mode"}
        >
          {themeMode === "dark" ? (
            <Sun className="h-4.5 w-4.5 text-nq-text-secondary" />
          ) : (
            <Moon className="h-4.5 w-4.5 text-nq-text-secondary" />
          )}
        </button>

        <button className="relative flex h-9 w-9 items-center justify-center rounded-nq hover:bg-nq-bg-card transition-colors">
          <Bell className="h-4.5 w-4.5 text-nq-text-secondary" />
          {alertCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-nq-bear text-[9px] font-bold text-white">
              {alertCount > 9 ? "9+" : alertCount}
            </span>
          )}
        </button>

        {/* Profile */}
        <button className="flex h-8 w-8 items-center justify-center rounded-full bg-nq-accent/10 text-sm font-bold text-nq-accent">
          NQ
        </button>
      </div>
    </header>
  );
}
