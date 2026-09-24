import re
with open('app/api/v1/watchlist.py', 'r') as f:
    content = f.read()

content = content.replace("from app.models.user import User", "from app.models.identity import User")

with open('app/api/v1/watchlist.py', 'w') as f:
    f.write(content)
