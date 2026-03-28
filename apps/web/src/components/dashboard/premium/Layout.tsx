"use client";

import { useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bell,
  Bot,
  ChartNoAxesCombined,
  Command,
  LayoutDashboard,
  Menu,
  Search,
  Shield,
  Sparkles,
  UserCircle2,
  X,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Tooltip } from "@/components/ui/Tooltip";
import { Button } from "./Button";

interface LayoutProps {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard, active: true },
  { href: "/terminal", label: "Terminal", icon: ChartNoAxesCombined, active: false },
  { href: "/research", label: "Research", icon: Bot, active: false },
  { href: "/portfolio", label: "Portfolio", icon: Shield, active: false },
];

function Sidebar({ onNavigate }: { onNavigate?: () => void }): JSX.Element {
  return (
    <aside className="flex h-full flex-col border-r border-white/10 bg-[rgba(9,12,20,0.8)] p-4 backdrop-blur-xl">
      <div className="mb-8 flex items-center gap-3 px-2 pt-2">
        <div className="rounded-xl bg-[var(--nq-accent)]/15 p-2 text-[var(--nq-accent)]">
          <Command className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-semibold text-[var(--nq-text-primary)]">NeuroQuant</p>
          <p className="text-xs text-[var(--nq-text-secondary)]">Control Center</p>
        </div>
      </div>

      <nav className="space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                item.active
                  ? "bg-[var(--nq-accent)]/15 text-[var(--nq-accent)]"
                  : "text-[var(--nq-text-secondary)] hover:bg-white/5 hover:text-[var(--nq-text-primary)]"
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto rounded-xl border border-white/10 bg-white/5 p-3">
        <p className="text-xs text-[var(--nq-text-secondary)]">Model Health</p>
        <div className="mt-2 flex items-center justify-between">
          <span className="text-sm font-medium text-[var(--nq-text-primary)]">96.2%</span>
          <Badge variant="buy">Healthy</Badge>
        </div>
      </div>
    </aside>
  );
}

export function Layout({ title, subtitle, children }: LayoutProps): JSX.Element {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="nq-premium-bg min-h-screen">
      <div className="pointer-events-none fixed inset-0 opacity-55">
        <div className="nq-grid-overlay h-full w-full" />
      </div>
      <div className="mx-auto grid min-h-screen max-w-[1600px] grid-cols-1 md:grid-cols-[260px_1fr]">
        <div className="hidden md:block">
          <Sidebar />
        </div>

        <div className="flex min-w-0 flex-col">
          <header className="sticky top-0 z-30 border-b border-white/10 bg-[rgba(7,9,15,0.72)] px-4 py-4 backdrop-blur-xl sm:px-6">
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="sm" className="md:hidden" onClick={() => setDrawerOpen(true)} leftIcon={<Menu className="h-4 w-4" />}>
                Menu
              </Button>

              <div className="hidden flex-1 items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 nq-soft-ring lg:flex">
                <Search className="h-4 w-4 text-[var(--nq-text-secondary)]" />
                <input
                  type="text"
                  placeholder="Search positions, symbols, reports..."
                  className="w-full bg-transparent text-sm text-[var(--nq-text-primary)] outline-none placeholder:text-[var(--nq-text-secondary)]"
                />
              </div>

              <div className="ml-auto flex items-center gap-2">
                <Tooltip content="Notifications" side="bottom">
                  <button className="rounded-xl border border-white/10 bg-white/5 p-2 text-[var(--nq-text-secondary)] transition hover:text-[var(--nq-text-primary)]">
                    <Bell className="h-4 w-4" />
                  </button>
                </Tooltip>
                <button className="rounded-xl border border-white/10 bg-white/5 p-2 text-[var(--nq-text-secondary)] transition hover:text-[var(--nq-text-primary)]">
                  <UserCircle2 className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div className="mt-5 flex flex-wrap items-start justify-between gap-3">
              <div>
                <h1 className="text-2xl font-semibold tracking-tight text-[var(--nq-text-primary)] sm:text-3xl">{title}</h1>
                <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-[var(--nq-text-secondary)]">{subtitle}</p>
              </div>
              <div className="inline-flex items-center gap-2">
                <Badge variant="outline" className="border-white/15 bg-white/5">March 28, 2026</Badge>
                <Badge variant="buy" className="inline-flex items-center gap-1"><Sparkles className="h-3 w-3" /> Premium</Badge>
              </div>
            </div>
          </header>

          <main className="relative z-10 flex-1 p-4 sm:p-6 lg:p-8">{children}</main>
        </div>
      </div>

      <AnimatePresence>
        {drawerOpen ? (
          <>
            <motion.button
              type="button"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setDrawerOpen(false)}
              className="fixed inset-0 z-40 bg-black/50 md:hidden"
              aria-label="Close drawer backdrop"
            />
            <motion.div
              initial={{ x: -320 }}
              animate={{ x: 0 }}
              exit={{ x: -320 }}
              transition={{ type: "spring", stiffness: 280, damping: 28 }}
              className="fixed left-0 top-0 z-50 h-full w-[280px] md:hidden"
            >
              <div className="absolute right-3 top-3 z-10">
                <button
                  type="button"
                  onClick={() => setDrawerOpen(false)}
                  className="rounded-lg border border-white/10 bg-white/10 p-1.5 text-[var(--nq-text-primary)]"
                  aria-label="Close mobile drawer"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <Sidebar onNavigate={() => setDrawerOpen(false)} />
            </motion.div>
          </>
        ) : null}
      </AnimatePresence>
    </div>
  );
}
