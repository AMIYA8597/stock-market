import Link from "next/link";
import { PublicLayout } from "./PublicLayout";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/dashboard/premium";
import { ShieldCheck, Sparkles, Workflow } from "lucide-react";

export function AuthLayout({ children }: { children: React.ReactNode }): JSX.Element {
  return (
    <PublicLayout>
      <section className="mx-auto grid min-h-[calc(100vh-4rem)] w-full max-w-[1600px] items-center gap-8 px-4 py-10 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:px-8">
        <Card glow className="relative overflow-hidden p-0">
          <div className="absolute inset-0 bg-[radial-gradient(1000px_520px_at_0%_0%,rgba(0,212,245,0.18),transparent_45%),radial-gradient(800px_420px_at_100%_0%,rgba(139,92,246,0.14),transparent_45%)]" />
          <div className="relative p-8 sm:p-10">
            <Badge variant="bull" className="px-3 py-1.5 text-[10px] uppercase tracking-[0.16em]">
              Secure workflow
            </Badge>
            <h1 className="mt-4 max-w-xl text-4xl font-semibold tracking-tight text-[var(--nq-text-primary)] sm:text-5xl">
              AI-native market operating system for modern teams.
            </h1>
            <p className="mt-4 max-w-lg text-sm leading-7 text-[var(--nq-text-secondary)] sm:text-base">
              Unify research, predictions, execution, and risk controls in one premium workspace built for scale and trust.
            </p>

            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <Workflow className="h-4.5 w-4.5 text-[var(--nq-accent)]" />
                <p className="mt-3 text-sm font-medium text-[var(--nq-text-primary)]">Workflow depth</p>
                <p className="mt-1 text-xs text-[var(--nq-text-secondary)]">Research to execution</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <ShieldCheck className="h-4.5 w-4.5 text-[var(--nq-bull)]" />
                <p className="mt-3 text-sm font-medium text-[var(--nq-text-primary)]">Security first</p>
                <p className="mt-1 text-xs text-[var(--nq-text-secondary)]">RBAC and MFA ready</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <Sparkles className="h-4.5 w-4.5 text-[var(--nq-accent)]" />
                <p className="mt-3 text-sm font-medium text-[var(--nq-text-primary)]">Premium UI</p>
                <p className="mt-1 text-xs text-[var(--nq-text-secondary)]">Responsive and polished</p>
              </div>
            </div>
          </div>
        </Card>
        <div>{children}</div>
      </section>
      <footer className="border-t border-white/10 py-4 text-center text-xs text-[var(--nq-text-muted)]">
        <Link href="/" className="transition hover:text-[var(--nq-text-secondary)]">
          NeuroQuant
        </Link>{" "}
        - Secure enterprise access
      </footer>
    </PublicLayout>
  );
}
