import re

with open('d:/work/stock-market/backend/app/database/connection.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('settings.DATABASE_URL,', 'settings.DATABASE_URL or "postgresql+asyncpg://postgres:postgres@localhost:5432/neuroquant_stage1",')

with open('d:/work/stock-market/backend/app/database/connection.py', 'w', encoding='utf-8') as f:
    f.write(content)
