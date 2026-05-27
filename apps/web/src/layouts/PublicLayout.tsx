"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, BarChart3, BrainCircuit, Menu, Sparkles, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/dashboard/premium";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/blog", label: "Blog" },
  { href: "/pricing", label: "Pricing" },
  { href: "/dashboard", label: "Dashboard" },
];

export function PublicLayout({ children }: { children: React.ReactNode }): JSX.Element {
  const pathname = usePathname();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="relative min-h-screen overflow-hidden bg-[var(--nq-bg-primary)] text-[var(--nq-text-primary)]">
      <div className="pointer-events-none fixed inset-0 opacity-80">
        <div className="nq-premium-bg h-full w-full" />
        <div className="nq-grid-overlay absolute inset-0 opacity-30" />
        <div className="absolute left-[-6rem] top-[-5rem] h-72 w-72 rounded-full bg-[rgba(0,212,245,0.12)] blur-3xl" />
        <div className="absolute right-[-7rem] top-[6rem] h-80 w-80 rounded-full bg-[rgba(139,92,246,0.14)] blur-3xl" />
      </div>

      <header className="sticky top-0 z-40 border-b border-white/10 bg-[rgba(7,9,15,0.74)] backdrop-blur-2xl">
        <div className="mx-auto flex h-16 max-w-[1600px] items-center gap-4 px-4 sm:px-6 lg:px-8">
          <Link href="/" className="inline-flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,var(--nq-accent),#65f7d2)] text-black shadow-[0_12px_28px_rgba(0,212,245,0.22)]">
              <BrainCircuit className="h-5 w-5" />
            </div>
            <div className="hidden sm:block">
              <p className="text-sm font-semibold tracking-tight text-[var(--nq-text-primary)]">NeuroQuant</p>
              <p className="text-[11px] text-[var(--nq-text-secondary)]">Market intelligence platform</p>
            </div>
          </Link>

          <nav className="hidden items-center gap-1 rounded-full border border-white/10 bg-white/5 p-1 lg:flex">
            {navItems.map((item) => {
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "rounded-full px-4 py-2 text-sm font-medium transition-all duration-200",
                    active
                      ? "bg-white/[0.10] text-[var(--nq-text-primary)] shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]"
                      : "text-[var(--nq-text-secondary)] hover:text-[var(--nq-text-primary)]"
                  )}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="ml-auto hidden items-center gap-2 md:flex">
            <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-[var(--nq-text-secondary)]">
              <span className="inline-flex h-2 w-2 rounded-full bg-[var(--nq-bull)] mr-2" />
              Live market state
            </div>
            <Link href="/login">
              <Button variant="ghost" size="sm">Sign in</Button>
            </Link>
            <Link href="/register">
              <Button size="sm" rightIcon={<ArrowRight className="h-4 w-4" />}>Start free</Button>
            </Link>
          </div>

          <button
            type="button"
            onClick={() => setMobileNavOpen((value) => !value)}
            className="ml-auto inline-flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-[var(--nq-text-primary)] lg:hidden"
            aria-label="Toggle navigation"
          >
            {mobileNavOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>

        <AnimatePresence>
          {mobileNavOpen ? (
            <motion.div
              initial={{ opacity: 0, y: -12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.2 }}
              className="border-t border-white/10 bg-[rgba(8,10,16,0.96)] px-4 py-4 lg:hidden"
            >
              <div className="mx-auto max-w-[1600px] space-y-3">
                {navItems.map((item) => {
                  const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setMobileNavOpen(false)}
                      className={cn(
                        "flex items-center justify-between rounded-[1rem] border border-white/10 px-4 py-3 text-sm transition",
                        active ? "bg-white/[0.08] text-[var(--nq-text-primary)]" : "bg-white/[0.04] text-[var(--nq-text-secondary)]"
                      )}
                    >
                      <span>{item.label}</span>
                      <ArrowRight className="h-4 w-4" />
                    </Link>
                  );
                })}

                <div className="grid grid-cols-2 gap-3 pt-2">
                  <Link href="/login" onClick={() => setMobileNavOpen(false)}>
                    <Button variant="secondary" className="w-full">Sign in</Button>
                  </Link>
                  <Link href="/register" onClick={() => setMobileNavOpen(false)}>
                    <Button className="w-full">Start free</Button>
                  </Link>
                </div>
              </div>
            </motion.div>
          ) : null}
        </AnimatePresence>
      </header>

      <main className="relative z-10">{children}</main>

      <footer className="relative z-10 border-t border-white/10 bg-[rgba(7,9,15,0.74)] backdrop-blur-2xl">
        <div className="mx-auto grid max-w-[1600px] gap-6 px-4 py-10 sm:px-6 lg:grid-cols-[1.2fr_0.8fr] lg:px-8">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[linear-gradient(135deg,var(--nq-accent),#65f7d2)] text-black">
                <BarChart3 className="h-5 w-5" />
              </div>
              <div>
                <p className="font-semibold text-[var(--nq-text-primary)]">NeuroQuant</p>
                <p className="text-sm text-[var(--nq-text-secondary)]">Premium AI stock intelligence</p>
              </div>
            </div>
            <p className="max-w-xl text-sm leading-7 text-[var(--nq-text-secondary)]">
              Built for institutional workflows: research, market monitoring, execution, and portfolio oversight in one scalable interface.
            </p>
            <div className="flex flex-wrap gap-2">
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-[var(--nq-text-secondary)]">React</span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-[var(--nq-text-secondary)]">Next.js</span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-[var(--nq-text-secondary)]">Framer Motion</span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-[var(--nq-text-secondary)]">Tailwind</span>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-[1.25rem] border border-white/10 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Explore</p>
              <div className="mt-3 space-y-2 text-sm text-[var(--nq-text-secondary)]">
                <Link href="/dashboard" className="block transition hover:text-[var(--nq-text-primary)]">Dashboard</Link>
                <Link href="/blog" className="block transition hover:text-[var(--nq-text-primary)]">Blog</Link>
                <Link href="/pricing" className="block transition hover:text-[var(--nq-text-primary)]">Pricing</Link>
              </div>
            </div>
            <div className="rounded-[1.25rem] border border-white/10 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">Status</p>
              <div className="mt-3 space-y-2 text-sm text-[var(--nq-text-secondary)]">
                <p className="inline-flex items-center gap-2"><Sparkles className="h-4 w-4 text-[var(--nq-accent)]" /> 99.98% platform uptime</p>
                <p className="inline-flex items-center gap-2"><Sparkles className="h-4 w-4 text-[var(--nq-bull)]" /> Live model feed active</p>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}