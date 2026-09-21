with open("backend/app/core/schema.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "from alembic.script import" in line:
        new_lines.append("        from alembic.script import ScriptDirectory\n")
    elif "from alembic.config import" in line:
        new_lines.append("        from alembic.config import Config\n")
    else:
        new_lines.append(line)

with open("backend/app/core/schema.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
