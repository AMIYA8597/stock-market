export default function LoadingTerminalPage(): JSX.Element {
  return (
    <main className="min-h-screen bg-[var(--nq-bg-base)] p-4 text-[var(--nq-text-primary)] sm:p-6">
      <div className="h-8 w-56 animate-pulse rounded bg-[rgba(255,255,255,0.08)]" />
      <div className="mt-4 grid gap-4 lg:grid-cols-[280px_1fr_320px]">
        <div className="h-80 animate-pulse rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)]" />
        <div className="h-80 animate-pulse rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)]" />
        <div className="h-80 animate-pulse rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)]" />
      </div>
    </main>
  );
}
