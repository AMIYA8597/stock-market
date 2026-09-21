import asyncio
import os
import sys
from urllib.parse import urlparse

import asyncpg

async def test_connection():
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgresql+asyncpg"):
        db_url = db_url.replace("postgresql+asyncpg", "postgresql")
    if not db_url:
        print("[X] ERROR: DATABASE_URL environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    parsed_url = urlparse(db_url)
    if not parsed_url.hostname or not parsed_url.username:
        print("[X] ERROR: DATABASE_URL must include a host and user.", file=sys.stderr)
        sys.exit(1)
        
    print("=========================================================")
    print("Testing connection to Database...")
    print("=========================================================")
    
    try:
        conn = await asyncio.wait_for(asyncpg.connect(db_url), timeout=10.0)
        
        version = await conn.fetchval("SELECT version();")
        user = await conn.fetchval("SELECT current_user;")
        
        print("\n[OK] SUCCESS! Connected to Database.")
        print(f"Host: {parsed_url.hostname}")
        print(f"Port: {parsed_url.port or 5432}")
        print(f"Configured user: {parsed_url.username}")
        print(f"Server role: {user}")
        print(f"Database Engine: {version}")
        
        await conn.close()
        
    except asyncio.TimeoutError:
        print("\n[X] ERROR: Connection Timed Out (TimeoutError)", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n[X] ERROR: {type(e).__name__} - {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_connection())
