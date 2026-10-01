export default function TerminalLoading() {
  return (
    <div className="flex h-screen items-center justify-center bg-[var(--nq-bg-base)]">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 rounded-full border-2 border-[var(--nq-accent-cyan)] border-t-transparent animate-spin" />
        <span className="text-sm text-[var(--nq-text-secondary)]">Loading Terminal...</span>
      </div>
    </div>
  );
}
