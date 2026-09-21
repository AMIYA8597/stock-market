import re
with open("backend/app/models/__init__.py", "r", encoding="utf-8") as f:
    content = f.read()

if "csrf_token" not in content:
    content = content.replace("from app.models.auth_token import", "from app.models.csrf_token import CSRFToken\nfrom app.models.auth_token import")
    with open("backend/app/models/__init__.py", "w", encoding="utf-8") as f:
        f.write(content)
