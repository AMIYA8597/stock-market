"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, TrendingUp, Briefcase, Menu, TerminalSquare } from "lucide-react";
import { cn } from "@neuroquant/ui";
import { useUIStore } from "@/stores/ui-store";

export function BottomNav() {
  const pathname = usePathname();
  const { toggleMobileSidebar } = useUIStore();

  const primaryRoutes = [
    { label: "Terminal", href: "/terminal", icon: TerminalSquare },
    { label: "Markets", href: "/markets", icon: TrendingUp },
    { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { label: "Portfolio", href: "/portfolio", icon: Briefcase },
  ];

  return (
    <nav className="fixed bottom-0 left-0 z-40 w-full border-t border-nq-border bg-[var(--nq-bg-card)] pb-[env(safe-area-inset-bottom)] lg:hidden">
      <div className="flex h-16 items-center justify-around px-2">
        {primaryRoutes.map((route) => {
          const isActive = pathname === route.href || pathname.startsWith(route.href + "/");
          const Icon = route.icon;
          return (
            <Link
              key={route.href}
              href={route.href}
              className={cn(
                "flex flex-1 flex-col items-center justify-center gap-1 rounded-lg py-2 transition-colors",
                isActive ? "text-nq-accent" : "text-nq-text-secondary hover:text-nq-text-primary"
              )}
            >
              <Icon className="h-5 w-5" />
              <span className="text-[10px] font-medium">{route.label}</span>
            </Link>
          );
        })}
        <button
          type="button"
          onClick={toggleMobileSidebar}
          aria-label="Open navigation menu"
          className="flex flex-1 flex-col items-center justify-center gap-1 rounded-lg py-2 text-nq-text-secondary hover:text-nq-text-primary transition-colors"
        >
          <Menu className="h-5 w-5" />
          <span className="text-[10px] font-medium">Menu</span>
        </button>
      </div>
    </nav>
  );
}
