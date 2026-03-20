import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Settings",
};

export default function SettingsPage(): JSX.Element {
  return (
    <main className="min-h-[calc(100vh-7rem)] rounded-xl border border-[var(--nq-border)] bg-[var(--nq-bg-surface)] p-4 sm:p-6 lg:p-8 text-[var(--nq-text-primary)]">
      <h1 className="text-xl font-semibold sm:text-2xl">Settings</h1>
      <p className="mt-2 max-w-2xl text-sm text-[var(--nq-text-secondary)]">
        Configure platform preferences, notifications, and terminal defaults.
      </p>

      <section className="mt-6 grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] p-4">
          <h2 className="text-sm font-medium">Appearance</h2>
          <p className="mt-1 text-xs text-[var(--nq-text-secondary)]">Typography, chart density, and watchlist defaults.</p>
        </div>
        <div className="rounded-lg border border-[var(--nq-border)] bg-[rgba(255,255,255,0.02)] p-4">
          <h2 className="text-sm font-medium">Notifications</h2>
          <p className="mt-1 text-xs text-[var(--nq-text-secondary)]">Signal alerts, regime transitions, and execution reminders.</p>
        </div>
      </section>
    </main>
  );
}
