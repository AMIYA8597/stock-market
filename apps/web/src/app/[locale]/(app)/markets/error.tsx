"use client";

export default function MarketsError({ error, reset }: { error: Error; reset: () => void }): JSX.Element {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[var(--nq-bg-base)] p-6 text-[var(--nq-text-primary)]">
      <div className="w-full max-w-lg rounded border border-[rgba(255,59,92,0.35)] bg-[var(--nq-bg-card)] p-4">
        <h1 className="text-lg font-semibold">Markets page failed to load</h1>
        <p className="mt-2 text-sm text-[var(--nq-text-secondary)]">{error.message}</p>
        <button onClick={reset} className="mt-4 rounded bg-[var(--nq-accent-cyan)] px-3 py-2 text-sm font-semibold text-[#07111A]">Retry</button>
      </div>
    </main>
  );
}
