"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Monitor,
  LayoutDashboard,
  TrendingUp,
  Briefcase,
  Search,
  FlaskConical,
  BookOpen,
  Bell,
  Settings,
  Receipt,
  ChevronLeft,
  ChevronRight,
  Brain,
} from "lucide-react";
import { cn } from "@neuroquant/ui";
import { useUIStore } from "@/stores/ui-store";

const navItems = [
  { label: "Terminal", href: "/terminal", icon: LayoutDashboard },
  { label: "Markets", href: "/markets", icon: TrendingUp },
  { label: "Research", href: "/research", icon: BookOpen },
  { label: "Backtest Lab", href: "/backtest-lab", icon: FlaskConical },
  { label: "Portfolio", href: "/portfolio", icon: Briefcase },
  { label: "Orders", href: "/portfolio/orders", icon: Receipt },
  { label: "Screener", href: "/screener", icon: Search },
  { label: "Alerts", href: "/alerts", icon: Bell },
  { label: "Model Monitor", href: "/model-monitor", icon: Monitor },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebar, mobileSidebarOpen, closeMobileSidebar } = useUIStore();

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-nq-border bg-nq-bg-secondary transition-all duration-300",
        "w-56 lg:translate-x-0",
        mobileSidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
        sidebarCollapsed ? "lg:w-16" : "lg:w-56"
      )}
    >
      {/* Logo */}
      <div className="flex h-14 items-center gap-2 border-b border-nq-border px-4">
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-nq bg-nq-accent/10">
          <Brain className="h-5 w-5 text-nq-accent" />
        </div>
        {!sidebarCollapsed && (
          <span className="font-display text-base font-bold nq-gradient-text">
            NeuroQuant
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-2 py-4">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={closeMobileSidebar}
              className={cn(
                "flex items-center gap-3 rounded-nq px-3 py-2 text-sm font-medium transition-all duration-150",
                isActive
                  ? "bg-nq-accent/10 text-nq-accent"
                  : "text-nq-text-secondary hover:bg-nq-bg-card hover:text-nq-text-primary",
                sidebarCollapsed && "lg:justify-center lg:px-0"
              )}
              title={sidebarCollapsed ? item.label : undefined}
            >
              <Icon className={cn("h-4.5 w-4.5 flex-shrink-0", isActive && "text-nq-accent")} />
              {(!sidebarCollapsed || mobileSidebarOpen) && <span>{item.label}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-nq-border p-2">
        <Link
          href="/settings"
          onClick={closeMobileSidebar}
          className={cn(
            "flex items-center gap-3 rounded-nq px-3 py-2 text-sm text-nq-text-secondary hover:bg-nq-bg-card hover:text-nq-text-primary transition-colors",
            sidebarCollapsed && "lg:justify-center lg:px-0"
          )}
        >
          <Settings className="h-4.5 w-4.5 flex-shrink-0" />
          {(!sidebarCollapsed || mobileSidebarOpen) && <span>Settings</span>}
        </Link>

        <button
          onClick={toggleSidebar}
          className="mt-1 hidden w-full items-center justify-center rounded-nq py-2 text-nq-text-tertiary transition-colors hover:bg-nq-bg-card hover:text-nq-text-secondary lg:flex"
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>
    </aside>
  );
}
