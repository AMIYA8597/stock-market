## Summary

<!-- What changed and why? Link the roadmap phase or issue. -->

## Test plan

- [ ] Backend: `uv run ruff check . && uv run mypy app/ && uv run pytest tests/`
- [ ] Frontend: `pnpm --filter @neuroquant/web run type-check && pnpm build`
- [ ] E2E: `pnpm --filter @neuroquant/web exec playwright test --retries=0`
- [ ] Honesty guard: `python scripts/honesty_guard.py`

## Checklist

- [ ] No `.env` files, keys, passwords, or tokens committed
- [ ] No test weakened or deleted to make CI pass
- [ ] Every reported number comes from a command run in this PR
