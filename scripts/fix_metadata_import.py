with open("backend/app/database/connection.py", "r", encoding="utf-8") as f:
    content = f.read()
if "from sqlalchemy import MetaData" not in content:
    content = content.replace("from sqlalchemy.orm import", "from sqlalchemy import MetaData\nfrom sqlalchemy.orm import")
    with open("backend/app/database/connection.py", "w", encoding="utf-8") as f:
        f.write(content)
