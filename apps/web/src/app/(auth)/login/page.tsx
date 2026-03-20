import Link from "next/link";

export default function LoginPage(): JSX.Element {
  return (
    <main className="min-h-screen bg-[radial-gradient(1200px_500px_at_20%_-10%,rgba(0,212,255,0.18),transparent_55%),radial-gradient(900px_420px_at_95%_10%,rgba(0,230,118,0.16),transparent_58%),var(--nq-bg-base)] px-4 py-10 text-[var(--nq-text-primary)] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-md rounded-xl border border-[var(--nq-border)] bg-[rgba(8,14,24,0.88)] p-5 shadow-[0_24px_80px_rgba(0,0,0,0.35)] sm:p-6">
        <p className="mb-2 text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">NeuroQuant Access</p>
        <h1 className="text-2xl font-semibold">Sign in</h1>
        <p className="mt-1 text-sm text-[var(--nq-text-secondary)]">Continue to the trading terminal, research workbench, and model monitoring suite.</p>

        <form className="mt-6 space-y-3">
          <label className="block">
            <span className="mb-1 block text-xs text-[var(--nq-text-secondary)]">Email</span>
            <input
              type="email"
              placeholder="you@domain.com"
              className="w-full rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-2 text-sm outline-none transition focus:border-[var(--nq-border-hover)]"
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-xs text-[var(--nq-text-secondary)]">Password</span>
            <input
              type="password"
              placeholder="Enter password"
              className="w-full rounded border border-[var(--nq-border)] bg-[var(--nq-bg-card)] px-3 py-2 text-sm outline-none transition focus:border-[var(--nq-border-hover)]"
            />
          </label>

          <button
            type="button"
            className="w-full rounded bg-[var(--nq-accent-cyan)] px-4 py-2 text-sm font-semibold text-[#041018] transition hover:brightness-110"
          >
            Sign in
          </button>
        </form>

        <p className="mt-4 text-sm text-[var(--nq-text-secondary)]">
          New here? <Link href="/register" className="text-[var(--nq-accent-cyan)] hover:underline">Create account</Link>
        </p>
      </div>
    </main>
  );
}
