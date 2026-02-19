"use client";

import { cn } from "@neuroquant/ui";
import { useUIStore } from "@/stores/ui-store";
import { useWebSocket } from "@/hooks/use-websocket";
import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { CommandPalette } from "./command-palette";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { sidebarCollapsed } = useUIStore();
  const { connectionStatus, alerts } = useWebSocket("/ws/alerts");

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div
        className={cn(
          "flex flex-1 flex-col transition-all duration-300",
          sidebarCollapsed ? "ml-16" : "ml-56"
        )}
      >
        <Topbar
          connectionStatus={connectionStatus}
          alertCount={alerts.filter((a) => !a.payload?.read).length}
        />
        <main className="flex-1 p-6">{children}</main>
      </div>
      <CommandPalette />
    </div>
  );
}
