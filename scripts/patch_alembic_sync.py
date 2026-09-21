import re
with open("backend/alembic/env.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace async_engine_from_config with engine_from_config
new_online = """def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.MIGRATIONS_DATABASE_URL
    from sqlalchemy import engine_from_config

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()"""

content = re.sub(r"async def run_async_migrations\(\) -> None:.*?asyncio\.run\(run_async_migrations\(\)\)", new_online, content, flags=re.DOTALL)

with open("backend/alembic/env.py", "w", encoding="utf-8") as f:
    f.write(content)
