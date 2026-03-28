"use client";

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Menu, Search, Sun, Moon, Command, ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Avatar } from '@/components/ui/Avatar';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Dropdown, DropdownContent, DropdownItem, DropdownLabel, DropdownSeparator, DropdownTrigger } from '@/components/ui/Dropdown';
import { Drawer } from '@/components/ui/Drawer';
import { NotificationMenu } from '@/modules/notifications/NotificationMenu';
import { ToastViewport } from '@/modules/notifications/ToastViewport';
import { CommandPalette } from '@/components/layout/command-palette';
import { dashboardNavItems } from './navigation';
import { useUIStore } from '@/stores/ui-store';

export function DashboardLayout({ children }: { children: React.ReactNode }): JSX.Element {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const {
    sidebarCollapsed,
    toggleSidebar,
    mobileSidebarOpen,
    openMobileSidebar,
    closeMobileSidebar,
    toggleMobileSidebar,
    openCommandPalette,
    themeMode,
    toggleThemeMode,
  } = useUIStore();

  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('nq_access_token') : null;
    if (!token) {
      router.replace('/login');
      return;
    }
    setReady(true);
  }, [router]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center ds-app-bg text-sm text-[var(--ds-text-secondary)]">
        Loading secure workspace...
      </div>
    );
  }

  return (
    <div className="min-h-screen ds-app-bg text-[var(--ds-text-primary)]">
      <motion.aside
        initial={{ x: -14, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.35 }}
        className={cn(
          'fixed left-0 top-0 z-40 hidden h-screen border-r border-[var(--ds-border-subtle)] bg-[var(--ds-surface-1)]/90 px-3 py-4 backdrop-blur-md lg:block',
          sidebarCollapsed ? 'w-20' : 'w-72'
        )}
      >
        <div className={cn('mb-6 flex items-center', sidebarCollapsed ? 'justify-center' : 'justify-between')}>
          <Link href="/dashboard" className="inline-flex items-center gap-2">
            <div className="h-9 w-9 rounded-[var(--ds-radius-lg)] bg-[var(--ds-color-primary-400)]/20" />
            {!sidebarCollapsed ? <span className="font-semibold">NeuroQuant</span> : null}
          </Link>
          {!sidebarCollapsed ? (
            <Button variant="ghost" size="icon" onClick={toggleSidebar}><ChevronLeft className="h-4 w-4" /></Button>
          ) : null}
        </div>
        <nav className="space-y-1.5">
          {dashboardNavItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 rounded-[var(--ds-radius-lg)] px-3 py-2 text-sm transition-all duration-300',
                  active ? 'bg-[var(--ds-color-primary-400)]/15 text-[var(--ds-color-primary-200)]' : 'text-[var(--ds-text-secondary)] hover:bg-[var(--ds-surface-2)] hover:text-[var(--ds-text-primary)]',
                  sidebarCollapsed && 'justify-center'
                )}
                title={sidebarCollapsed ? item.label : undefined}
              >
                <Icon className="h-4.5 w-4.5 shrink-0" />
                {!sidebarCollapsed ? <span>{item.label}</span> : null}
              </Link>
            );
          })}
        </nav>
        {sidebarCollapsed ? (
          <div className="mt-3 flex justify-center"><Button variant="ghost" size="icon" onClick={toggleSidebar}><ChevronRight className="h-4 w-4" /></Button></div>
        ) : null}
      </motion.aside>

      <Drawer open={mobileSidebarOpen} onOpenChange={(open) => (open ? openMobileSidebar() : closeMobileSidebar())} title="Navigation" side="left">
        <nav className="space-y-1.5">
          {dashboardNavItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={closeMobileSidebar}
                className={cn(
                  'flex items-center gap-3 rounded-[var(--ds-radius-lg)] px-3 py-2 text-sm transition',
                  active ? 'bg-[var(--ds-color-primary-400)]/15 text-[var(--ds-color-primary-200)]' : 'text-[var(--ds-text-secondary)] hover:bg-[var(--ds-surface-2)] hover:text-[var(--ds-text-primary)]'
                )}
              >
                <Icon className="h-4.5 w-4.5" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </Drawer>

      <div className={cn('transition-all duration-300', sidebarCollapsed ? 'lg:ml-20' : 'lg:ml-72')}>
        <header className="sticky top-0 z-30 border-b border-[var(--ds-border-subtle)] bg-[var(--ds-surface-1)]/82 px-4 py-3 backdrop-blur-md sm:px-6">
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.32 }} className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="icon" className="lg:hidden" onClick={toggleMobileSidebar}><Menu className="h-4 w-4" /></Button>
              <div className="relative hidden w-[320px] md:block">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--ds-text-muted)]" />
                <Input className="pl-9" placeholder="Search markets, docs, pages..." />
              </div>
              <Button variant="secondary" size="sm" className="hidden md:inline-flex" onClick={openCommandPalette}><Command className="mr-1 h-4 w-4" /> Command</Button>
            </div>
            <div className="flex items-center gap-1.5">
              <Button variant="ghost" size="icon" onClick={toggleThemeMode}>
                {themeMode === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
              </Button>
              <NotificationMenu />
              <Dropdown>
                <DropdownTrigger asChild>
                  <button className="rounded-full">
                    <Avatar fallback="NQ" />
                  </button>
                </DropdownTrigger>
                <DropdownContent align="end">
                  <DropdownLabel>Account</DropdownLabel>
                  <DropdownSeparator />
                  <DropdownItem>Profile</DropdownItem>
                  <DropdownItem>Settings</DropdownItem>
                  <DropdownItem>Sign out</DropdownItem>
                </DropdownContent>
              </Dropdown>
            </div>
          </motion.div>
        </header>
        <main className="px-4 py-5 sm:px-6 sm:py-6">
          <div className="ds-page-transition">{children}</div>
        </main>
      </div>
      <CommandPalette />
      <ToastViewport />
    </div>
  );
}
