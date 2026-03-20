export default function LoadingBacktestLabPage(): JSX.Element {
  return (
    <main className="min-h-screen bg-[var(--nq-bg-base)] p-6 text-[var(--nq-text-primary)]">
      <div className="h-8 w-56 animate-pulse rounded bg-[rgba(255,255,255,0.08)]" />
      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[2fr_3fr]">
        <div className="h-96 animate-pulse rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)]" />
        <div className="h-96 animate-pulse rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)]" />
      </div>
    </main>
  );
}
