import re
import os

# 1. Rename in connection.py
with open("backend/app/database/connection.py", "r", encoding="utf-8") as f:
    content = f.read()
content = content.replace("async def init_db() -> None:", "async def create_all_for_tests() -> None:")
with open("backend/app/database/connection.py", "w", encoding="utf-8") as f:
    f.write(content)

# 2. Update __init__.py if it is exported
init_path = "backend/app/database/__init__.py"
if os.path.exists(init_path):
    with open(init_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("init_db", "create_all_for_tests")
    with open(init_path, "w", encoding="utf-8") as f:
        f.write(content)

# 3. Update app/core/database.py if it exports it
core_db_path = "backend/app/core/database.py"
if os.path.exists(core_db_path):
    with open(core_db_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("init_db", "create_all_for_tests")
    with open(core_db_path, "w", encoding="utf-8") as f:
        f.write(content)

# 4. Patch tests/conftest.py
conftest_path = "backend/tests/conftest.py"
if os.path.exists(conftest_path):
    with open(conftest_path, "r", encoding="utf-8") as f:
        content = f.read()
    content = content.replace("init_db", "create_all_for_tests")
    with open(conftest_path, "w", encoding="utf-8") as f:
        f.write(content)

# 5. Patch events.py
with open("backend/app/core/events.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace the db block
db_block_pattern = re.compile(r"# \S+ Initialize Database \S+\n.*?logger\.warning\(\"Database is offline\. REST services accessing DB will fail\.\"\)", re.DOTALL)
new_db_block = """# \u2500\u2500\u2500 Initialize Database \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        logger.info("startup_database_init")
        try:
            from app.core.database import engine

            # Test database connection
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1") if hasattr(conn, "execute") else "SELECT 1")
            logger.info("startup_database_success", database_url=settings.DATABASE_URL)

            # Schema guard is called dynamically by the schema middleware, but we can also do a quick check here.
        except Exception as e:
            logger.error("startup_database_failed", error=str(e), exc_info=True)
            logger.warning("Database is offline. REST services accessing DB will fail.")"""

content = db_block_pattern.sub(new_db_block, content)
with open("backend/app/core/events.py", "w", encoding="utf-8") as f:
    f.write(content)
