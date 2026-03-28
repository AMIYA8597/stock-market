import Link from 'next/link';
import { ArrowRight, ShieldCheck, Sparkles, TrendingUp, Workflow } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardContent } from '@/components/ui/Card';

const features = [
  {
    icon: TrendingUp,
    title: 'Live Multi-Asset Intelligence',
    description: 'Track equities, crypto, forex, and macro factors in one unified command view.',
  },
  {
    icon: Workflow,
    title: 'End-to-End Quant Workflow',
    description: 'Research, backtest, execute, and monitor model health without context switching.',
  },
  {
    icon: ShieldCheck,
    title: 'Enterprise Risk Controls',
    description: 'Policy-based guardrails and drift alerts keep production strategies reliable.',
  },
];

const testimonials = [
  { quote: 'NeuroQuant reduced our strategy iteration cycle from weeks to hours.', name: 'Priya Mehta', role: 'Head of Quant, Arclight Capital' },
  { quote: 'The platform feels like Stripe-level polish for serious market teams.', name: 'Jonathan Cruz', role: 'CTO, Selene Funds' },
  { quote: 'From backtests to production monitoring, every surface finally feels connected.', name: 'Aarav Kapoor', role: 'Lead PM, Orion Trading' },
];

export function LandingPage(): JSX.Element {
  return (
    <div>
      <section className="relative overflow-hidden border-b border-[var(--ds-border-subtle)] px-4 py-20 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <div className="max-w-3xl">
            <p className="inline-flex items-center gap-1 rounded-full border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-2)] px-3 py-1 text-xs uppercase tracking-[0.12em] text-[var(--ds-text-secondary)]">
              <Sparkles className="h-3.5 w-3.5" />
              Institutional-grade AI investing workspace
            </p>
            <h1 className="mt-5 text-[var(--ds-heading-1)] font-semibold leading-tight">Operate your full investment stack from one premium control plane.</h1>
            <p className="mt-5 max-w-2xl text-base text-[var(--ds-text-secondary)]">NeuroQuant unifies live market data, model intelligence, execution tooling, and risk analytics into one deliberate, high-performance SaaS experience.</p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link href="/register"><Button size="lg">Start free trial <ArrowRight className="ml-1 h-4 w-4" /></Button></Link>
              <Link href="/dashboard"><Button variant="outline" size="lg">Explore product</Button></Link>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-4 px-4 py-16 sm:px-6 md:grid-cols-2 lg:grid-cols-3 lg:px-8">
        {features.map((feature) => {
          const Icon = feature.icon;
          return (
            <Card key={feature.title} className="border-[var(--ds-border-subtle)] bg-[var(--ds-surface-1)]/85">
              <CardContent className="p-5">
                <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-[var(--ds-radius-lg)] bg-[var(--ds-color-primary-400)]/16">
                  <Icon className="h-5 w-5 text-[var(--ds-color-primary-300)]" />
                </div>
                <h3 className="text-lg font-semibold">{feature.title}</h3>
                <p className="mt-2 text-sm text-[var(--ds-text-secondary)]">{feature.description}</p>
              </CardContent>
            </Card>
          );
        })}
      </section>

      <section className="border-t border-[var(--ds-border-subtle)] px-4 py-14 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <h2 className="text-[var(--ds-heading-2)] font-semibold">Trusted by teams running real capital</h2>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {testimonials.map((item) => (
              <Card key={item.name} className="border-[var(--ds-border-subtle)] bg-[var(--ds-surface-1)]/80">
                <CardContent className="p-5">
                  <p className="text-sm text-[var(--ds-text-secondary)]">"{item.quote}"</p>
                  <p className="mt-4 text-sm font-semibold">{item.name}</p>
                  <p className="text-xs text-[var(--ds-text-muted)]">{item.role}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
