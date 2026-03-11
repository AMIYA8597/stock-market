#!/usr/bin/env python3
"""
Phase 1 Database Test - Simple connection test
Tests PostgreSQL + TimescaleDB connectivity and basic table creation
"""

import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker

async def test_database_connection():
    """Test database connection and basic functionality."""
    
    # Database URL from environment
    database_url = "postgresql+asyncpg://neuroquant:neuroquant_dev_2024@localhost:5432/neuroquant_db"
    
    print("🔍 Testing Phase 1: Database + Migrations")
    print("=" * 50)
    
    try:
        # Create async engine
        print("1. Creating database engine...")
        engine = create_async_engine(
            database_url,
            echo=True,  # Show SQL for debugging
            pool_size=5,
            max_overflow=10
        )
        
        # Test connection
        print("2. Testing database connection...")
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Connected to PostgreSQL: {version[:50]}...")
        
        # Test TimescaleDB extension
        print("3. Checking TimescaleDB extension...")
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'"))
            ts_version = result.scalar()
            if ts_version:
                print(f"✅ TimescaleDB extension found: {ts_version}")
            else:
                print("⚠️  TimescaleDB extension not found")
        
        # Test basic table creation
        print("4. Creating test table...")
        async with engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS test_table (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    data TEXT
                )
            """))
            print("✅ Test table created successfully")
        
        # Test hypertable creation
        print("5. Creating TimescaleDB hypertable...")
        async with engine.begin() as conn:
            # Drop if exists to test creation
            await conn.execute(text("DROP TABLE IF EXISTS test_hypertable CASCADE"))
            
            # Create regular table first
            await conn.execute(text("""
                CREATE TABLE test_hypertable (
                    time TIMESTAMPTZ NOT NULL,
                    symbol TEXT NOT NULL,
                    value NUMERIC(18,4),
                    PRIMARY KEY (time, symbol)
                )
            """))
            
            # Convert to hypertable
            await conn.execute(text("""
                SELECT create_hypertable('test_hypertable', 'time', chunk_time_interval => INTERVAL '1 day')
            """))
            print("✅ Hypertable created successfully")
        
        # Test data insertion
        print("6. Testing data insertion...")
        async with engine.begin() as conn:
            await conn.execute(text("""
                INSERT INTO test_hypertable (time, symbol, value) VALUES
                (NOW(), 'TEST', 100.50),
                (NOW() - INTERVAL '1 hour', 'TEST', 101.25),
                (NOW() - INTERVAL '2 hours', 'TEST', 99.75)
            """))
            print("✅ Data inserted successfully")
        
        # Test data retrieval
        print("7. Testing data retrieval...")
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT symbol, COUNT(*) as count, AVG(value) as avg_value
                FROM test_hypertable
                GROUP BY symbol
            """))
            rows = result.fetchall()
            for row in rows:
                print(f"   Symbol: {row[0]}, Count: {row[1]}, Avg: {row[2]:.2f}")
            print("✅ Data retrieved successfully")
        
        # Cleanup
        print("8. Cleaning up test objects...")
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS test_hypertable"))
            await conn.execute(text("DROP TABLE IF EXISTS test_table"))
            print("✅ Cleanup completed")
        
        await engine.dispose()
        
        print("\n🎉 Phase 1 Database Test - PASSED")
        print("=" * 50)
        print("✅ PostgreSQL connection working")
        print("✅ TimescaleDB extension available") 
        print("✅ Table creation working")
        print("✅ Hypertable creation working")
        print("✅ Data insertion/retrieval working")
        print("\n📋 Ready for Phase 2: Auth Service")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Phase 1 Database Test - FAILED")
        print(f"Error: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("1. Ensure PostgreSQL is running on localhost:5432")
        print("2. Ensure database 'neuroquant_db' exists")
        print("3. Ensure user 'neuroquant' has correct permissions")
        print("4. Check .env file database configuration")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database_connection())
    sys.exit(0 if success else 1)
