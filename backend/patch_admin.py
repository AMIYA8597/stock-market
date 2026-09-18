
path = 'app/api/v1/admin.py'
with open(path) as f:
    content = f.read()

# Add logging import
if "import logging" not in content:
    content = content.replace("import uuid", "import uuid\nimport logging\n\nlogger = logging.getLogger(__name__)")

# Log role update
content = content.replace("""    user.role = payload.role
    await db.commit()""", """    user.role = payload.role
    logger.info(f"Admin action: user {current_user.id} changed role of user {user_id} to {payload.role}")
    await db.commit()""")

with open(path, 'w') as f:
    f.write(content)
print("Admin logging patched!")
