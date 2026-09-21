import re
with open("backend/alembic/env.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add include_object
include_object_func = """
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and object.schema in ("auth", "storage", "realtime", "extensions", "graphql", "vault", "cron", "net", "supabase_migrations"):
        return False
    return True
"""
if "def include_object" not in content:
    content = content.replace("target_metadata = Base.metadata", "target_metadata = Base.metadata\n" + include_object_func)

# Fix do_run_migrations
do_run_pattern = re.compile(r"def do_run_migrations\(connection: Connection\) -> None:.*?context\.run_migrations\(\)", re.DOTALL)
new_do_run = """def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()"""
content = do_run_pattern.sub(new_do_run, content)

with open("backend/alembic/env.py", "w", encoding="utf-8") as f:
    f.write(content)
