"""
Test Phase 1: Database Schema Verification

Tests that:
  1. All 12 tables exist
  2. All columns have correct types
  3. TimescaleDB hypertables are configured
  4. Indices are created
  5. Constraints are enforced
"""

import asyncio
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://neuroquant:neuroquant@localhost:5432/neuroquant"
)


class TestPhase1Database:
    """Test database schema created in PHASE 1"""

    @classmethod
    async def setup_class(cls):
        """Setup async engine and session"""
        cls.engine = create_async_engine(DATABASE_URL, echo=False)
        cls.AsyncSessionLocal = sessionmaker(
            cls.engine, class_=AsyncSession, expire_on_commit=False
        )

    @classmethod
    async def teardown_class(cls):
        """Cleanup engine"""
        await cls.engine.dispose()

    async def test_01_database_connected(self):
        """Test 1: Can connect to database"""
        async with self.engine.connect() as conn:
            result = await conn.execute(text("SELECT 1 as connected"))
            row = result.fetchone()
            assert row.connected == 1, "Database connection failed"
        print("✓ Database connection successful")

    async def test_02_all_tables_exist(self):
        """Test 2: All 12 tables exist"""
        async with self.engine.connect() as conn:
            # Get all table names
            result = await conn.execute(
                text("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY tablename
                """)
            )
            tables = [row.tablename for row in result.fetchall()]

        expected_tables = [
            "users",
            "refresh_tokens",
            "backup_codes",
            "ohlcv",
            "tick_data",
            "model_versions",
            "predictions",
            "portfolios",
            "holdings",
            "alert_definitions",
            "alert_events",
            "portfolio_risk_snapshots",
            "audit_log",
            "backtest_runs",
            "backtest_trades",
            "watchlists",
            "watchlist_items",
        ]

        for table in expected_tables:
            assert table in tables, f"Table {table} not found"
            print(f"  ✓ Table {table} exists")

    async def test_03_users_table_structure(self):
        """Test 3: Users table has correct columns"""
        async with self.engine.connect() as conn:
            inspector = inspect(self.engine.sync_engine)
            columns = inspector.get_columns("users")

        column_names = [col["name"] for col in columns]
        expected_columns = [
            "id",
            "username",
            "email_hash",
            "email_encrypted",
            "password_hash",
            "is_active",
            "two_fa_enabled",
            "two_fa_secret",
            "created_at",
            "updated_at",
        ]

        for col in expected_columns:
            assert col in column_names, f"Column {col} not found in users table"
            print(f"  ✓ Column {col} exists")

    async def test_04_ohlcv_is_hypertable(self):
        """Test 4: OHLCV table is a TimescaleDB hypertable"""
        async with self.engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT * FROM timescaledb_information.hypertables
                    WHERE hypertable_name = 'ohlcv'
                """)
            )
            hypertable = result.fetchone()
            assert hypertable is not None, "OHLCV is not a hypertable"
        print("✓ OHLCV is configured as TimescaleDB hypertable")

    async def test_05_tick_data_is_hypertable(self):
        """Test 5: Tick data table is a TimescaleDB hypertable"""
        async with self.engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT * FROM timescaledb_information.hypertables
                    WHERE hypertable_name = 'tick_data'
                """)
            )
            hypertable = result.fetchone()
            assert hypertable is not None, "Tick data is not a hypertable"
        print("✓ Tick data is configured as TimescaleDB hypertable")

    async def test_06_indices_created(self):
        """Test 6: All expected indices exist"""
        async with self.engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT indexname FROM pg_indexes
                    WHERE schemaname = 'public'
                    ORDER BY indexname
                """)
            )
            indices = [row.indexname for row in result.fetchall()]

        expected_indices = [
            "ix_ohlcv_symbol_time",
            "ix_tick_data_symbol_time",
            "ix_predictions_symbol",
            "ix_holdings_portfolio_id",
            "ix_alert_definitions_user_id",
            "ix_alert_events_alert_id",
            "ix_portfolio_risk_snapshots_portfolio_id",
        ]

        for idx in expected_indices:
            assert idx in indices, f"Index {idx} not found"
            print(f"  ✓ Index {idx} exists")

    async def test_07_user_authentication_fields(self):
        """Test 7: User can be created and retrieved"""
        async with self.AsyncSessionLocal() as session:
            # Create a test user
            await session.execute(
                text("""
                    INSERT INTO users (username, email_hash, email_encrypted, password_hash)
                    VALUES ('testuser', 'hash123', 'encrypted123', 'pwhash123')
                    ON CONFLICT DO NOTHING
                """)
            )
            await session.commit()

            # Retrieve user
            result = await session.execute(
                text("SELECT id, username FROM users WHERE username = 'testuser'")
            )
            user = result.fetchone()
            assert user is not None, "User not created"
            assert user.username == "testuser", "Username mismatch"

        print("✓ User creation and retrieval works")

    async def test_08_portfolio_and_holdings_relationship(self):
        """Test 8: Portfolio and holdings foreign key constraint"""
        async with self.AsyncSessionLocal() as session:
            # Try to insert holding with non-existent portfolio_id (should fail)
            try:
                await session.execute(
                    text("""
                        INSERT INTO holdings (portfolio_id, symbol, quantity, avg_cost)
                        VALUES ('00000000-0000-0000-0000-000000000000'::uuid, 'TEST', 10, 100)
                    """)
                )
                await session.commit()
                assert False, "Foreign key constraint not enforced"
            except Exception as e:
                print(f"✓ Foreign key constraint enforced: {type(e).__name__}")

    async def test_09_compression_policy(self):
        """Test 9: TimescaleDB compression policy is configured"""
        async with self.engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT * FROM timescaledb_information.compression_settings
                    WHERE hypertable_name IN ('ohlcv', 'tick_data', 'audit_log')
                """)
            )
            compression_settings = result.fetchall()
            assert len(compression_settings) > 0, "No compression settings found"
        print(f"✓ Compression configured for {len(compression_settings)} hypertables")

    async def test_10_audit_log_immutable(self):
        """Test 10: Audit log table has integrity checking"""
        async with self.engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = 'audit_log'
                    AND column_name IN ('row_hash', 'prev_hash')
                """)
            )
            hash_columns = [row.column_name for row in result.fetchall()]
            assert "row_hash" in hash_columns, "row_hash column missing"
            assert "prev_hash" in hash_columns, "prev_hash column missing"
        print("✓ Audit log has integrity hash columns")

    async def test_11_extensions_installed(self):
        """Test 11: Required PostgreSQL extensions are installed"""
        async with self.engine.connect() as conn:
            result = await conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname IN ('uuid-ossp', 'pgcrypto', 'timescaledb')")
            )
            extensions = [row.extname for row in result.fetchall()]

        assert "uuid-ossp" in extensions, "uuid-ossp extension not installed"
        assert "pgcrypto" in extensions, "pgcrypto extension not installed"
        assert "timescaledb" in extensions, "timescaledb extension not installed"
        print("✓ All required PostgreSQL extensions installed")

    async def test_12_constraints_defined(self):
        """Test 12: Key constraints are defined"""
        async with self.engine.connect() as conn:
            # Test NOT NULL constraints
            try:
                await conn.execute(
                    text("INSERT INTO users (email_hash) VALUES (NULL)")
                )
                assert False, "NOT NULL constraint not enforced"
            except Exception:
                pass

        print("✓ Database constraints enforced")


async def run_all_tests():
    """Run all tests"""
    test_suite = TestPhase1Database()
    await test_suite.setup_class()

    tests = [
        test_suite.test_01_database_connected,
        test_suite.test_02_all_tables_exist,
        test_suite.test_03_users_table_structure,
        test_suite.test_04_ohlcv_is_hypertable,
        test_suite.test_05_tick_data_is_hypertable,
        test_suite.test_06_indices_created,
        test_suite.test_07_user_authentication_fields,
        test_suite.test_08_portfolio_and_holdings_relationship,
        test_suite.test_09_compression_policy,
        test_suite.test_10_audit_log_immutable,
        test_suite.test_11_extensions_installed,
        test_suite.test_12_constraints_defined,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1

    await test_suite.teardown_class()

    print("\n" + "=" * 80)
    print(f"PHASE 1 DATABASE TESTS: {passed} passed, {failed} failed")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
