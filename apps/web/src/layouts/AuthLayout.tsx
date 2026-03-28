import Link from 'next/link';
import { PublicLayout } from './PublicLayout';

export function AuthLayout({ children }: { children: React.ReactNode }): JSX.Element {
  return (
    <PublicLayout>
      <section className="mx-auto grid min-h-[calc(100vh-4rem)] w-full max-w-7xl items-center gap-8 px-4 py-8 sm:px-6 lg:grid-cols-[1.1fr_0.9fr] lg:px-8">
        <div className="relative overflow-hidden rounded-[var(--ds-radius-2xl)] border border-[var(--ds-border-subtle)] bg-[linear-gradient(160deg,rgba(13,148,203,0.25),rgba(13,22,40,0.18))] p-8 shadow-[var(--ds-shadow-lg)]">
          <div className="ds-grid-overlay absolute inset-0 opacity-35" />
          <div className="relative">
            <p className="text-xs uppercase tracking-[0.16em] text-[var(--ds-text-secondary)]">Institutional Workflow</p>
            <h1 className="mt-3 max-w-sm text-4xl font-semibold leading-tight">AI-native market operating system for modern teams.</h1>
            <p className="mt-4 max-w-md text-sm text-[var(--ds-text-secondary)]">Unify research, predictions, execution, and risk controls in one premium workspace built for scale.</p>
            <div className="mt-8 space-y-3 text-sm text-[var(--ds-text-secondary)]">
              <p>Real-time model monitoring</p>
              <p>Role-based admin controls</p>
              <p>Automated strategy backtesting</p>
            </div>
          </div>
        </div>
        <div>{children}</div>
      </section>
      <footer className="border-t border-[var(--ds-border-subtle)] py-4 text-center text-xs text-[var(--ds-text-muted)]">
        <Link href="/" className="transition hover:text-[var(--ds-text-secondary)]">NeuroQuant</Link> - Secure enterprise access
      </footer>
    </PublicLayout>
  );
}
