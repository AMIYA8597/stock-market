with open("backend/tests/integration/test_api_backtest.py", "r") as f:
    code = f.read()

replacement = """
    async def execute(self, statement, *args, **kwargs):
        from sqlalchemy.sql import Select
        if isinstance(statement, Select):
            entity = statement.column_descriptions[0]["entity"]
            if entity.__name__ == "PlanEntitlement":
                class MockResult:
                    def scalars(self):
                        class MockScalars:
                            def first(self):
                                return True
                        return MockScalars()
                return MockResult()
"""

# Replace the execute method
import re
code = re.sub(r'    async def execute\(self, statement, \*args, \*\*kwargs\):.*?            except Exception:\n                pass\n\n            class MockResult:\n                def __init__\(self, items\):\n                    self\.items = items\n\n                def scalar_one_or_none\(self\):\n                    return self\.items\[0\] if self\.items else None\n\n                def scalars\(self\):\n                    class MockScalars:\n                        def __init__\(self, it\):\n                            self\.it = it\n                        def all\(self\):\n                            return self\.it\n                        def first\(self\):\n                            return self\.it\[0\] if self\.it else None\n                    return MockScalars\(self\.items\)\n\n            return MockResult\(objs\)', 
"""    async def execute(self, statement, *args, **kwargs):
        from sqlalchemy.sql import Select
        if isinstance(statement, Select):
            entity = statement.column_descriptions[0]["entity"]
            if entity.__name__ == "PlanEntitlement":
                class MockResult:
                    def scalars(self):
                        class MockScalars:
                            def first(self):
                                return True
                        return MockScalars()
                return MockResult()
            objs = [v for v in self.store.values() if isinstance(v, entity)]
            try:
                params = statement.compile().params
                for k, v in params.items():
                    if "user_id" in k:
                        objs = [x for x in objs if getattr(x, "user_id", None) == uuid.UUID(str(v))]
                    elif "id" in k or k == "id_1" or k == "id":
                        if isinstance(v, (str, uuid.UUID)):
                            try:
                                objs = [x for x in objs if getattr(x, "id", None) == uuid.UUID(str(v))]
                            except Exception: pass
            except Exception: pass
            class MockResult:
                def __init__(self, items): self.items = items
                def scalar_one_or_none(self): return self.items[0] if self.items else None
                def scalars(self):
                    class MockScalars:
                        def __init__(self, it): self.it = it
                        def all(self): return self.it
                        def first(self): return self.it[0] if self.it else None
                    return MockScalars(self.items)
            return MockResult(objs)""", code, flags=re.DOTALL)

with open("backend/tests/integration/test_api_backtest.py", "w") as f:
    f.write(code)

print("Fixed execute mock!")
