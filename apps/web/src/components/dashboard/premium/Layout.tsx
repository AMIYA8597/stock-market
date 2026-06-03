"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  BrainCircuit,
  ChevronDown,
  Command,
  Menu,
  Moon,
  Search,
  Settings,
  Sparkles,
  Sun,
  UserCircle2,
} from "lucide-react";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { Dropdown, DropdownContent, DropdownItem, DropdownLabel, DropdownSeparator, DropdownTrigger } from "@/components/ui/Dropdown";
import { Drawer } from "@/components/ui/Drawer";
import { Input } from "@/components/ui/Input";
import { Tooltip } from "@/components/ui/Tooltip";
import { NotificationMenu } from "@/modules/notifications/NotificationMenu";
import { ToastViewport } from "@/modules/notifications/ToastViewport";
import { CommandPalette } from "@/components/layout/command-palette";
import { useUIStore } from "@/stores/ui-store";
import { cn } from "@/lib/utils";
import { dashboardNavItems } from "@/layouts/navigation";
import { Button } from "./Button";

interface LayoutProps {
  children: React.ReactNode;
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }): JSX.Element {
  const pathname = usePathname();

  return (
    <aside className="flex h-full flex-col border-r border-white/10 bg-[rgba(8,10,16,0.82)] p-4 backdrop-blur-2xl">
      <div className="mb-8 flex items-center gap-3 rounded-[1.25rem] border border-white/10 bg-white/5 p-3 shadow-[0_16px_40px_rgba(0,0,0,0.18)]">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,var(--nq-accent),#65f7d2)] text-black shadow-[0_14px_30px_rgba(0,212,245,0.2)]">
          <BrainCircuit className="h-5 w-5" />
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold tracking-tight text-[var(--nq-text-primary)]">NeuroQuant</p>
            <Badge variant="bull" className="px-2 py-0.5 text-[10px] uppercase tracking-[0.12em]">
              Live
            </Badge>
          </div>
          <p className="mt-1 text-xs text-[var(--nq-text-secondary)]">Institutional control center</p>
        </div>
      </div>

      <nav className="space-y-1.5">
        {dashboardNavItems.map((item) => {
          const Icon = item.icon;
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname === item.href || pathname.startsWith(`${item.href}/`);

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={cn(
                "group flex items-center gap-3 rounded-[1rem] px-3 py-2.75 text-sm transition-all duration-200",
                active
                  ? "bg-[linear-gradient(135deg,rgba(0,212,245,0.16),rgba(255,255,255,0.04))] text-[var(--nq-text-primary)] shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]"
                  : "text-[var(--nq-text-secondary)] hover:bg-white/[0.06] hover:text-[var(--nq-text-primary)]"
              )}
            >
              <Icon className={cn("h-4.5 w-4.5 shrink-0 transition-colors", active && "text-[var(--nq-accent)]")} />
              <span className="font-medium">{item.label}</span>
              {active ? <span className="ml-auto h-2 w-2 rounded-full bg-[var(--nq-accent)] shadow-[0_0_12px_rgba(0,212,245,0.7)]" /> : null}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto space-y-3">
        <div className="rounded-[1.25rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-4 shadow-[0_16px_40px_rgba(0,0,0,0.2)]">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">System health</p>
              <p className="mt-2 text-2xl font-semibold tracking-tight text-[var(--nq-text-primary)]">98.4%</p>
            </div>
            <Badge variant="buy" className="h-fit text-[10px] uppercase tracking-[0.12em]">
              Optimal
            </Badge>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
            <div className="rounded-2xl border border-white/[0.08] bg-white/5 p-3">
              <p className="text-[var(--nq-text-secondary)]">Latency</p>
              <p className="mt-1 text-sm font-semibold text-[var(--nq-text-primary)]">42 ms</p>
            </div>
            <div className="rounded-2xl border border-white/[0.08] bg-white/5 p-3">
              <p className="text-[var(--nq-text-secondary)]">Signals</p>
              <p className="mt-1 text-sm font-semibold text-[var(--nq-text-primary)]">17 live</p>
            </div>
          </div>
        </div>

        <button
          type="button"
          className="flex w-full items-center justify-between rounded-[1rem] border border-white/10 bg-white/5 px-3.5 py-3 text-sm text-[var(--nq-text-secondary)] transition hover:bg-white/[0.08] hover:text-[var(--nq-text-primary)]"
          onClick={onNavigate}
        >
          <span className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Workspace settings
          </span>
          <Settings className="h-4 w-4" />
        </button>
      </div>
    </aside>
  );
}

export function Layout({ children }: LayoutProps): JSX.Element {
  const { mobileSidebarOpen, openMobileSidebar, closeMobileSidebar, openCommandPalette, themeMode, toggleThemeMode, toggleMobileSidebar } = useUIStore();

  return (
    <div className="relative min-h-screen overflow-hidden bg-[var(--nq-bg-primary)] text-[var(--nq-text-primary)]">
      <div className="pointer-events-none fixed inset-0 opacity-80">
        <div className="nq-premium-bg h-full w-full" />
        <div className="nq-grid-overlay absolute inset-0 opacity-35" />
        <div className="nq-float absolute left-[-8rem] top-[-5rem] h-72 w-72 rounded-full bg-[rgba(0,212,245,0.13)] blur-3xl" />
        <div className="nq-float absolute right-[-6rem] top-[8rem] h-80 w-80 rounded-full bg-[rgba(139,92,246,0.14)] blur-3xl [animation-delay:1.8s]" />
        <div className="nq-float absolute bottom-[-7rem] left-[36%] h-80 w-80 rounded-full bg-[rgba(0,230,118,0.07)] blur-3xl [animation-delay:3.3s]" />
      </div>

      <div className="relative mx-auto grid min-h-screen max-w-[1680px] grid-cols-1 lg:grid-cols-[286px_minmax(0,1fr)]">
        <div className="hidden lg:block">
          <Sidebar />
        </div>

        <div className="flex min-w-0 flex-col">
          <header className="sticky top-0 z-30 border-b border-white/10 bg-[rgba(7,9,15,0.76)] px-4 py-4 backdrop-blur-2xl sm:px-6">
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="icon" className="lg:hidden" onClick={toggleMobileSidebar} aria-label="Open navigation">
                <Menu className="h-4 w-4" />
              </Button>

              <Button variant="secondary" size="sm" className="hidden md:inline-flex" onClick={openCommandPalette} leftIcon={<Command className="h-4 w-4" />}>
                Command
              </Button>

              <Tooltip content="Open search" side="bottom">
                <button
                  type="button"
                  onClick={openCommandPalette}
                  className="hidden min-w-0 flex-1 items-center gap-3 rounded-[1rem] border border-white/10 bg-white/5 px-4 py-2.5 text-left text-sm text-[var(--nq-text-secondary)] transition hover:border-white/15 hover:bg-white/[0.08] hover:text-[var(--nq-text-primary)] md:flex"
                >
                  <Search className="h-4 w-4 shrink-0" />
                  <span className="truncate">Search markets, positions, reports, and pages</span>
                  <kbd className="ml-auto inline-flex items-center gap-1 rounded-lg border border-white/10 bg-white/[0.08] px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--nq-text-secondary)]">
                    <Command className="h-3 w-3" />K
                  </kbd>
                </button>
              </Tooltip>

              <Tooltip content="Quick search" side="bottom">
                <button
                  type="button"
                  onClick={openCommandPalette}
                  className="flex h-10 w-10 items-center justify-center rounded-[1rem] border border-white/10 bg-white/5 text-[var(--nq-text-secondary)] transition hover:bg-white/[0.08] hover:text-[var(--nq-text-primary)] md:hidden"
                  aria-label="Open search"
                >
                  <Search className="h-4 w-4" />
                </button>
              </Tooltip>

              <div className="ml-auto flex items-center gap-2 sm:gap-3">
                <Badge variant="bull" className="hidden items-center gap-1.5 px-3 py-1.5 text-[10px] uppercase tracking-[0.16em] sm:inline-flex">
                  <span className="h-1.5 w-1.5 rounded-full bg-current" />
                  Live feed
                </Badge>

                <Tooltip content="Toggle theme" side="bottom">
                  <button
                    type="button"
                    onClick={toggleThemeMode}
                    className="flex h-10 w-10 items-center justify-center rounded-[1rem] border border-white/10 bg-white/5 text-[var(--nq-text-secondary)] transition hover:bg-white/[0.08] hover:text-[var(--nq-text-primary)]"
                    aria-label="Toggle theme"
                  >
                    {themeMode === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
                  </button>
                </Tooltip>

                <NotificationMenu />

                <Dropdown>
                  <DropdownTrigger asChild>
                    <button className="flex items-center gap-2 rounded-[1rem] border border-white/10 bg-white/5 px-2.5 py-2 text-left text-sm text-[var(--nq-text-secondary)] transition hover:bg-white/[0.08] hover:text-[var(--nq-text-primary)]">
                      <Avatar fallback="NQ" className="h-8 w-8 border-white/10 bg-white/[0.08]" />
                      <div className="hidden sm:block">
                        <p className="text-sm font-semibold text-[var(--nq-text-primary)]">NeuroQuant</p>
                        <p className="text-[11px] text-[var(--nq-text-secondary)]">Portfolio ops</p>
                      </div>
                      <ChevronDown className="h-4 w-4 text-[var(--nq-text-secondary)]" />
                    </button>
                  </DropdownTrigger>
                  <DropdownContent align="end" className="w-56">
                    <DropdownLabel>Workspace</DropdownLabel>
                    <DropdownSeparator />
                    <DropdownItem>
                      <UserCircle2 className="mr-2 h-4 w-4" />
                      Profile
                    </DropdownItem>
                    <DropdownItem>
                      <Settings className="mr-2 h-4 w-4" />
                      Settings
                    </DropdownItem>
                    <DropdownItem>
                      <Sparkles className="mr-2 h-4 w-4" />
                      Upgrade plan
                    </DropdownItem>
                  </DropdownContent>
                </Dropdown>
              </div>
            </div>
          </header>

          <main className="relative flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }} className="mx-auto max-w-[1600px]">
              {children}
            </motion.div>
          </main>
        </div>
      </div>

      <Drawer open={mobileSidebarOpen} onOpenChange={(open) => (open ? openMobileSidebar() : closeMobileSidebar())} title="Navigation" side="left">
        <div className="space-y-5">
          <Input placeholder="Search markets or pages" className="h-11 bg-white/[0.06]" />
          <Sidebar onNavigate={closeMobileSidebar} />
        </div>
      </Drawer>

      <CommandPalette />
      <ToastViewport />
    </div>
  );
}