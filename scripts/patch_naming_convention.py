import re
with open("backend/app/database/connection.py", "r", encoding="utf-8") as f:
    content = f.read()

import_line = "from sqlalchemy.orm import DeclarativeBase, sessionmaker"
if import_line not in content:
    # Try another way
    pass

new_import = "from sqlalchemy import MetaData\nfrom sqlalchemy.orm import DeclarativeBase, sessionmaker"
content = content.replace(import_line, new_import)

naming_convention_code = """NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)"""

content = re.sub(r"class Base\(DeclarativeBase\):", naming_convention_code, content)

with open("backend/app/database/connection.py", "w", encoding="utf-8") as f:
    f.write(content)
