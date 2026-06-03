"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { cn } from "@neuroquant/ui";
import { useUIStore } from "@/stores/ui-store";
import { usePriceFeed } from "@/hooks/usePriceFeed";
import { alertsApi } from "@/lib/api-client";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { CommandPalette } from "./command-palette";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { sidebarCollapsed, mobileSidebarOpen, closeMobileSidebar } = useUIStore();
  const { status: connectionStatus } = usePriceFeed(["NIFTY50"]);
  const [alertCount, setAlertCount] = useState<number>(0);

  useEffect(() => {
    let mounted = true;

    async function loadAlerts(): Promise<void> {
      try {
        const data = await alertsApi.getHistory(20);
        if (!mounted) {
          return;
        }
        setAlertCount(data.length);
      } catch {
        if (mounted) {
          setAlertCount(0);
        }
      }
    }

    void loadAlerts();
    const intervalId = setInterval(() => {
      void loadAlerts();
    }, 30_000);

    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, []);

  const pathname = usePathname();
  const isTerminal = pathname === "/";

  return (
    <div className="flex min-h-screen bg-[var(--nq-bg-base)]">
      <Sidebar />
      {mobileSidebarOpen ? (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={closeMobileSidebar}
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
        />
      ) : null}
      <div
        className={cn(
          "flex flex-1 flex-col transition-all duration-300 min-h-screen overflow-hidden",
          sidebarCollapsed ? "lg:ml-16" : "lg:ml-56"
        )}
      >
        {!isTerminal && (
          <Topbar
            connectionStatus={connectionStatus}
            alertCount={alertCount}
          />
        )}
        <main className={cn("flex-1 min-h-0", !isTerminal && "p-3 sm:p-4 lg:p-6")}>{children}</main>
      </div>
      <CommandPalette />
    </div>
  );
}
