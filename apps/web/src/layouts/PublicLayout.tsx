import Link from 'next/link';
import { BarChart3, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export function PublicLayout({ children }: { children: React.ReactNode }): JSX.Element {
  return (
    <div className="min-h-screen ds-app-bg text-[var(--ds-text-primary)]">
      <header className="sticky top-0 z-30 border-b border-[var(--ds-border-subtle)] bg-[var(--ds-surface-1)]/85 backdrop-blur-md">
        <div className="mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link href="/" className="inline-flex items-center gap-2">
            <div className="inline-flex h-9 w-9 items-center justify-center rounded-[var(--ds-radius-lg)] bg-[var(--ds-color-primary-400)]/15">
              <BarChart3 className="h-5 w-5 text-[var(--ds-color-primary-300)]" />
            </div>
            <span className="font-semibold tracking-wide">NeuroQuant</span>
          </Link>
          <nav className="hidden items-center gap-7 text-sm text-[var(--ds-text-secondary)] md:flex">
            <Link href="/blog" className="transition hover:text-[var(--ds-text-primary)]">Blog</Link>
            <Link href="/pricing" className="transition hover:text-[var(--ds-text-primary)]">Pricing</Link>
            <Link href="/dashboard" className="transition hover:text-[var(--ds-text-primary)]">Dashboard</Link>
          </nav>
          <div className="flex items-center gap-2">
            <Link href="/login"><Button variant="ghost" size="sm">Sign in</Button></Link>
            <Link href="/register"><Button size="sm">Start Free <ChevronRight className="ml-1 h-4 w-4" /></Button></Link>
          </div>
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
}
