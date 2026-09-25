import app.database.connection as conn_module


def test_transaction_mode_cache_sizes(monkeypatch):
    # Mock settings
    class MockSettings:
        DEBUG = False
        DB_SSL_REQUIRED = True
        DB_POOL_MODE = "transaction"
        is_production = True
        DATABASE_URL = "postgresql+asyncpg://user:pass@host:5432/db"

    monkeypatch.setattr(conn_module, "settings", MockSettings())

    kwargs = conn_module._get_engine_kwargs()
    assert kwargs["poolclass"].__name__ == "NullPool"

    connect_args = kwargs.get("connect_args", {})
    assert connect_args.get("statement_cache_size") == 0
    assert connect_args.get("prepared_statement_cache_size") == 0
    assert connect_args.get("ssl") is True

def test_session_mode_pool_args(monkeypatch):
    class MockSettings:
        DEBUG = False
        DB_SSL_REQUIRED = False
        DB_POOL_MODE = "session"
        is_production = True
        DB_POOL_SIZE = 5
        DB_MAX_OVERFLOW = 2
        DB_POOL_RECYCLE = 1800
        DATABASE_URL = "postgresql+asyncpg://user:pass@host:5432/db"

    monkeypatch.setattr(conn_module, "settings", MockSettings())

    kwargs = conn_module._get_engine_kwargs()
    assert "poolclass" not in kwargs
    assert kwargs["pool_size"] == 5
    assert kwargs["max_overflow"] == 2

    connect_args = kwargs.get("connect_args", {})
    assert "statement_cache_size" not in connect_args
