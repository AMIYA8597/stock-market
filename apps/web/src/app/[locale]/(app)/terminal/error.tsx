"use client";

export default function TerminalError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="flex h-screen flex-col items-center justify-center gap-4 bg-[var(--nq-bg-base)] text-[var(--nq-text-primary)]">
      <div className="rounded-full bg-[rgba(255,59,92,0.1)] border border-[rgba(255,59,92,0.3)] p-4">
        <span className="text-2xl">!</span>
      </div>
      <h2 className="text-lg font-semibold">Terminal Error</h2>
      <p className="max-w-md text-center text-sm text-[var(--nq-text-secondary)]">{error.message}</p>
      <button
        onClick={reset}
        className="rounded border border-[var(--nq-accent-cyan)] bg-[rgba(0,212,245,0.1)] px-4 py-2 text-sm text-[var(--nq-accent-cyan)] hover:bg-[rgba(0,212,245,0.2)] transition-colors"
      >
        Try Again
      </button>
    </div>
  );
}
