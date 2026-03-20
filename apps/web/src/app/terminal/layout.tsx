import type { ReactNode } from "react";

export default function TerminalLayout({ children }: { children: ReactNode }): JSX.Element {
  return (
    <div className="min-h-screen bg-[radial-gradient(1000px_500px_at_10%_-20%,rgba(0,212,245,0.12),transparent_55%),radial-gradient(900px_420px_at_95%_0%,rgba(139,92,246,0.10),transparent_50%),var(--nq-bg-base)] text-[var(--nq-text-primary)]">
      {children}
    </div>
  );
}
