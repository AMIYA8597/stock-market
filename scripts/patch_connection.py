import re
with open("backend/app/database/connection.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace _get_engine_kwargs and engine creation
engine_block_pattern = re.compile(r"def _get_engine_kwargs\(\) -> dict:.*?engine = create_async_engine\(\n    settings\.DATABASE_URL,\n    \*\*_get_engine_kwargs\(\),\n\)", re.DOTALL)

new_engine_block = """def _get_engine_kwargs() -> dict:
    kwargs = {
        "echo": settings.DEBUG,
        "echo_pool": settings.DEBUG,
    }
    
    connect_args = {
        "server_settings": {"application_name": "neuroquant-api"},
        "command_timeout": 15.0  # roughly equivalent to statement_timeout for asyncpg
    }
    if settings.DB_SSL_REQUIRED:
        connect_args["ssl"] = True
        
    if settings.DB_POOL_MODE == "transaction":
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_cache_size"] = 0
        kwargs["poolclass"] = NullPool
    else:
        kwargs["poolclass"] = QueuePool
        kwargs["pool_size"] = settings.DB_POOL_SIZE
        kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE
        
    kwargs["connect_args"] = connect_args
    return kwargs

engine = create_async_engine(
    settings.DATABASE_URL,
    **_get_engine_kwargs(),
)"""

content = engine_block_pattern.sub(new_engine_block, content)

# Remove the postgres connection event listeners
event_pattern = re.compile(r"# \S+ Connection Pool Event Handlers \S+\n_is_postgres = settings\.DATABASE_URL\.startswith\(\"postgresql\"\)\n\nif _is_postgres:\n\n.*?else:\n    logger\.debug\(\n        \"database_skipping_postgres_listeners \(using %s\)\", settings\.DATABASE_URL\.split\(\":\"\)\[0\]\n    \)\n", re.DOTALL)
content = event_pattern.sub("", content)

# Fix settings references in logger below engine creation
content = content.replace("settings.DATABASE_POOL_SIZE", "settings.DB_POOL_SIZE")

with open("backend/app/database/connection.py", "w", encoding="utf-8") as f:
    f.write(content)
