export default function LoadingPortfolioPage(): JSX.Element {
  return (
    <main className="min-h-screen bg-[var(--nq-bg-base)] p-6 text-[var(--nq-text-primary)]">
      <div className="h-8 w-56 animate-pulse rounded bg-[rgba(255,255,255,0.08)]" />
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={`portfolio-load-${i}`} className="h-28 animate-pulse rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)]" />
        ))}
      </div>
    </main>
  );
}
