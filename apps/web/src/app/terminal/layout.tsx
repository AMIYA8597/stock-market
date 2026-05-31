import type { ReactNode } from "react";

export default function TerminalLayout({ children }: { children: ReactNode }): JSX.Element {
  return (
    <div className="min-h-screen bg-[var(--bg-base)] text-[var(--text-primary)]">
      {children}
    </div>
  );
}
