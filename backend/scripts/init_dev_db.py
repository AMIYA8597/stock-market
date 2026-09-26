"""Create SQLite dev DB tables using the project's SQLAlchemy models.

Run this after setting backend/.env (already created).
"""

import asyncio
import os
import sys

# Ensure backend path is on sys.path
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ENVIRONMENT", "development")


async def main():
    from app.database.connection import create_all_for_tests

    print("Initializing dev SQLite database...")
    await create_all_for_tests()
    print("Database initialized.")


if __name__ == "__main__":
    asyncio.run(main())
