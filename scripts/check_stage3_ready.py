"""Check Stage 3 prerequisites without mutating the database."""

from __future__ import annotations

import os
from datetime import date

REQUIRED_TABLES = {
    "feature_sets", "datasets", "experiments", "model_runs", "model_metrics",
    "model_registry", "prediction_outcomes", "drift_reports",
}
REQUIRED_BUCKETS = {"model-artifacts", "datasets"}


def check_database() -> tuple[list[str], list[str]]:  # noqa: C901
    passed: list[str] = []
    failed: list[str] = []
    url = os.getenv("DATABASE_URL") or os.getenv("MIGRATIONS_DATABASE_URL")
    if not url:
        return passed, ["database URL is not configured"]
    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        return passed, ["SQLAlchemy is unavailable in the active Python environment"]
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "+psycopg2")
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as connection:
            tables = {
                row[0]
                for row in connection.execute(text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                ))
            }
            missing = sorted(REQUIRED_TABLES - tables)
            if missing:
                failed.append(f"registry tables missing: {', '.join(missing)}")
            else:
                passed.append("registry tables present")

            if "storage" in tables:
                buckets = {
                    row[0]
                    for row in connection.execute(text("SELECT id FROM storage.buckets"))
                }
                missing = sorted(REQUIRED_BUCKETS - buckets)
                if missing:
                    failed.append(f"Storage buckets missing: {', '.join(missing)}")
                else:
                    passed.append("Storage buckets present")
            else:
                failed.append("Storage bucket metadata is unavailable")

            count, start_date, end_date = connection.execute(text(
                "SELECT COUNT(DISTINCT symbol_id), MIN(time), MAX(time) "
                "FROM ohlcv WHERE interval = '1d'"
            )).one()
            if count < 45:
                failed.append(f"daily bars cover {count} instruments; need at least 45")
            else:
                passed.append(f"daily bars cover {count} instruments")
            minimum = date.today().replace(year=date.today().year - 3)
            if start_date is None or start_date.date() > minimum:
                failed.append(f"daily bars do not reach the three-year minimum ({minimum})")
            else:
                passed.append(f"daily bars reach {start_date.date()} through {end_date.date()}")

            columns = {
                row[0]
                for row in connection.execute(text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'ohlcv'"
                ))
            }
            if "source" not in columns and "provenance" not in columns:
                failed.append("daily bars have no provenance column")
            else:
                passed.append("daily bar provenance column present")
    except Exception as exc:  # deployment infrastructure is optional locally
        failed.append(f"database check unavailable: {type(exc).__name__}")
    return passed, failed


def main() -> int:
    passed, failed = check_database()
    print("Stage 3 dependency checklist")
    for item in passed:
        print(f"[PASS] {item}")
    for item in failed:
        print(f"[FAIL] {item}")
    if failed:
        print("[FAIL] Stage 3 is blocked until all prerequisites pass")
        return 1
    print("[PASS] Stage 2 WP 2.4 DB-backed read services require deployment verification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
