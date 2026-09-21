import re
with open("scripts/check_db_connection.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("db_url = os.environ.get(\"DATABASE_URL\")", "db_url = os.environ.get(\"DATABASE_URL\")\n    if db_url and db_url.startswith(\"postgresql+asyncpg\"):\n        db_url = db_url.replace(\"postgresql+asyncpg\", \"postgresql\")")

content = content.replace("\\u274c", "[X]")
content = content.replace("o. SUCCESS!", "[OK] SUCCESS!")
content = content.replace("?O ERROR:", "[X] ERROR:")
content = content.replace("❌", "[X]")
content = content.replace("✅", "[OK]")

with open("scripts/check_db_connection.py", "w", encoding="utf-8") as f:
    f.write(content)
