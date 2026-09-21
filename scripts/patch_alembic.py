import re
with open("backend/alembic/env.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("settings.DATABASE_URL_SYNC", "settings.MIGRATIONS_DATABASE_URL")
content = content.replace("settings.DATABASE_URL", "settings.MIGRATIONS_DATABASE_URL")

with open("backend/alembic/env.py", "w", encoding="utf-8") as f:
    f.write(content)
