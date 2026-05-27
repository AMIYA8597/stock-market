"""Create SQLite dev DB tables using the project's SQLAlchemy models.

Run this after setting backend/.env (already created).
"""

import asyncio
import os

# Ensure backend path is on sys.path
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("ENVIRONMENT", "development")

async def main():
    from app.database.connection import init_db

    print("Initializing dev SQLite database...")
    await init_db()
    print("Database initialized.")

if __name__ == "__main__":
    asyncio.run(main())
