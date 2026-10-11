# STANDING RULES

## Git and delivery
- Work only in D:\work\stock-market. Session start: `git switch main; git pull --ff-only`;
  `git status` must be clean; `git config user.email` must be chowdhuryamiya41@gmail.com
  and user.name AMIYA8597 (fix if not, never use another identity).
- One branch + one PR per phase; split big phases into several PRs. Commit messages say why.
- Before every push, run the CI-equivalent locally; everything must pass:
  backend: uv run ruff check . ; uv run mypy app/ ; uv run pytest tests/ ;
           uv run alembic check  (against the local docker-compose Postgres, NEVER production)
  web:     pnpm --filter @neuroquant/web run type-check ; pnpm build ;
           pnpm --filter @neuroquant/web exec playwright test --retries=0
  repo:    python scripts/honesty_guard.py
- Push with my git credentials. Wait until EVERY PR check is green (backend, web, guard, e2e,
  Vercel). Then `gh pr merge <n> --merge`, `git switch main`, `git pull --ff-only`.
  Then watch the Cloud Run deploy and the smoke workflow until green.
- Never --force, never --no-verify, never commit .env files, keys, passwords or tokens.
- Deploys are automatic (GitHub Actions -> Cloud Run, Vercel git integration). Never deploy by hand.

## Honesty
- Every number you report (tests, latency, accuracy, returns, win rate, drawdown) must come from
  a command you ran in this session; otherwise write "not measured".
- Never write "guaranteed", "perfect win rate", "100% secure", "risk-free", "profitable" without
  measured evidence and its uncertainty.
- Never weaken or delete a test, the honesty guard or the stage-2 safety guard to make CI pass.
  Fix the code, or explain why the test is wrong and ask me first.
- Never invent data, metrics or model results. Fallback/placeholder output must be labelled in the UI.

## Data and safety
- Production data is real. Local dev and tests use docker-compose Postgres/Redis
  (backend/.env.local.example), never the production Supabase database.
- Real-money order placement stays disabled until Phase 9 and my written approval in chat.
- You may not create accounts or type passwords on the live site; ask me to do it.

## Context management
- Read only the files the current task needs; use subagents for wide searches.
- When the conversation gets long, update docs/PROGRESS.md, commit, and tell me to start a new session.
- End every session with: what changed, PR link, test output summary, what is still broken,
  exactly what you need from me.
