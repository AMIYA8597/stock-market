"use client";

export default function StocksError({ error, reset }: { error: Error; reset: () => void }): JSX.Element {
  return (
    <div className="rounded border border-[rgba(255,59,92,0.35)] bg-[var(--nq-bg-card)] p-4 text-[var(--nq-text-primary)]">
      <h2 className="text-base font-semibold">Stocks view failed</h2>
      <p className="mt-1 text-sm text-[var(--nq-text-secondary)]">{error.message}</p>
      <button onClick={reset} className="mt-3 rounded bg-[var(--nq-accent-cyan)] px-3 py-2 text-sm font-semibold text-[#07111A]">Retry</button>
    </div>
  );
}
