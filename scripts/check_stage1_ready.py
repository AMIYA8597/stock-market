"""Fail-fast Stage 1 prerequisite check for Stage 2 work."""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import asyncpg

REQUIRED_TABLES = {
    "organizations",
    "org_members",
    "usage_counters",
    "audit_log",
    "paper_accounts",
    "paper_ledger_entries",
    "payment_events",
    "model_registry",
    "quote_snapshots",
    "ingestion_runs",
    "market_calendar",
    "instrument_aliases",
    "ohlcv",
}


def database_url() -> str:
    value = os.environ.get("DATABASE_URL", "").strip()
    if value.startswith("postgresql+asyncpg://"):
        value = value.replace("postgresql+asyncpg://", "postgresql://", 1)
    if not value:
        raise RuntimeError("DATABASE_URL is not set")
    parsed = urlparse(value)
    if parsed.scheme != "postgresql" or not parsed.hostname or not parsed.username:
        raise RuntimeError("DATABASE_URL must be a PostgreSQL URL with a host and user")
    return value


def alembic_heads() -> set[str]:
    backend_dir = Path(__file__).resolve().parents[1] / "backend"
    result = subprocess.run(
        ["alembic", "heads"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("could not read Alembic heads")
    return set(re.findall(r"^([0-9a-f]+)\s+\(head\)", result.stdout, re.MULTILINE))


async def check() -> int:
    results: list[tuple[str, bool, str]] = []
    try:
        conn = await asyncio.wait_for(asyncpg.connect(database_url()), timeout=10)
    except Exception as exc:
        print(f"[FAIL] database connection: {type(exc).__name__}")
        return 1

    try:
        role = await conn.fetchval("SELECT current_user")
        results.append(("runtime role is not postgres", role != "postgres", str(role)))

        version = await conn.fetchval(
            "SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1"
        )
        results.append(
            ("Alembic head is applied", bool(version and version in alembic_heads()), str(version))
        )

        rows = await conn.fetch(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = ANY($1::text[])
            """,
            list(REQUIRED_TABLES),
        )
        present = {row["table_name"] for row in rows}
        missing = sorted(REQUIRED_TABLES - present)
        results.append(("required Stage 1 tables exist", not missing, ", ".join(missing) or "all present"))

        if present:
            rls_rows = await conn.fetch(
                """
                SELECT c.relname, c.relrowsecurity FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relname = ANY($1::text[])
                """,
                list(present),
            )
            unprotected = sorted(row["relname"] for row in rls_rows if not row["relrowsecurity"])
            results.append(("RLS enabled on Stage 1 tables", not unprotected, ", ".join(unprotected) or "all protected"))

        if "ohlcv" in present:
            coverage = await conn.fetchrow(
                """
                SELECT count(DISTINCT instrument_id) AS instruments, min(timestamp) AS oldest, max(timestamp) AS newest
                FROM ohlcv WHERE interval = '1d' AND timestamp >= now() - interval '1 year'
                """
            )
            enough = bool(coverage and coverage["instruments"] >= 5)
            detail = f"{coverage['instruments']} instruments, {coverage['oldest']} to {coverage['newest']}"
            results.append(("ohlcv has one year for at least five instruments", enough, detail))
    except Exception as exc:
        results.append(("database checks completed", False, type(exc).__name__))
    finally:
        await conn.close()

    print("Stage 1 readiness")
    for name, passed, detail in results:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    return 0 if all(passed for _, passed, _ in results) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(check()))
    except RuntimeError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
