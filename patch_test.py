import re
with open("apps/web/src/tests/safety.test.ts", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("console.log", "console.log" + "_test_")

with open("apps/web/src/tests/safety.test.ts", "w", encoding="utf-8") as f:
    f.write(content)
