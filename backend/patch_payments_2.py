
path = 'app/api/v1/payments.py'
with open(path) as f:
    content = f.read()

import_line = "from app.core.security import is_test_mode\n    "
target = """    else:
        # Mock mode fallback
        is_verified = True"""

replacement = """    elif is_test_mode():
        # Mock mode fallback ONLY allowed in tests
        is_verified = True
    else:
        is_verified = False"""

if target in content:
    content = content.replace("    is_verified = False\n    secret = getattr", import_line + "is_verified = False\n    secret = getattr")
    content = content.replace(target, replacement)
    with open(path, 'w') as f:
        f.write(content)
    print("SUCCESS!")
else:
    print("TARGET NOT FOUND IN PAYMENTS.PY")
