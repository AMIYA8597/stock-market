with open('app/api/v1/router.py', 'r') as f:
    content = f.read()

content = content.replace(
    'from app.api.v1 import (',
    'from app.api.v1 import (\n    organizations,'
)
content = content.replace(
    'router.include_router(users.router)',
    'router.include_router(users.router)\nrouter.include_router(organizations.router)'
)

with open('app/api/v1/router.py', 'w') as f:
    f.write(content)
