import re
with open("backend/app/core/schema.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("from alembic.script import ScriptDirectory", "")
content = content.replace("from alembic.config import Config", "")

import_alembic = """        from alembic.script import ScriptDirectory
        from alembic.config import Config
        alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini"))"""

content = content.replace("alembic_cfg = Config(os.path.join(os.path.dirname(__file__), \"..\", \"..\", \"alembic.ini\"))", import_alembic)

with open("backend/app/core/schema.py", "w", encoding="utf-8") as f:
    f.write(content)
