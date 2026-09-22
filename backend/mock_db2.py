from app.database.connection import engine
from sqlalchemy import text
import asyncio

async def run():
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS ohlcv"))
        for stmt in [
            'CREATE TABLE IF NOT EXISTS universes (id text primary key, name text)',
            'CREATE TABLE IF NOT EXISTS symbols (id text primary key, ticker text)',
            'CREATE TABLE IF NOT EXISTS universe_memberships (symbol_id text, universe_id text)',
            'CREATE TABLE ohlcv (time text, symbol_id text, open real, high real, low real, close real, volume real, adjusted_close real, interval text)',
            'CREATE TABLE IF NOT EXISTS datasets (id text primary key, content_hash text unique, row_count int, feature_set_id text, label_spec text, created_at text)',
            "INSERT OR IGNORE INTO universes VALUES ('1', 'NIFTY50')",
            "INSERT OR IGNORE INTO symbols VALUES ('1', 'RELIANCE')",
            "INSERT OR IGNORE INTO universe_memberships VALUES ('1', '1')"
        ]:
            await conn.execute(text(stmt))
            
        for i in range(1, 100):
            if i <= 31:
                await conn.execute(text(f"INSERT INTO ohlcv VALUES ('2019-01-{i:02d}', '1', 100, 105, 95, 101, 1000, 101, '1d')"))
            elif i <= 59:
                await conn.execute(text(f"INSERT INTO ohlcv VALUES ('2019-02-{i-31:02d}', '1', 100, 105, 95, 101, 1000, 101, '1d')"))
            elif i <= 90:
                await conn.execute(text(f"INSERT INTO ohlcv VALUES ('2019-03-{i-59:02d}', '1', 100, 105, 95, 101, 1000, 101, '1d')"))
            else:
                await conn.execute(text(f"INSERT INTO ohlcv VALUES ('2019-04-{i-90:02d}', '1', 100, 105, 95, 101, 1000, 101, '1d')"))

asyncio.run(run())
